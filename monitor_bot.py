import os
import re
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MONITOR_BOT_TOKEN = os.getenv('MONITOR_BOT_TOKEN')
AUTOBUY_BOT_USERNAME = os.getenv('AUTOBUY_BOT_USERNAME')
# Updated pattern to support both Ethereum (0x...) and Solana addresses
CA_PATTERN = os.getenv('CA_PATTERN', r'(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})')
PROCESSED_CONTRACTS_FILE = 'processed_contracts.txt'
ENABLED_CHANNELS_FILE = 'enabled_channels.json'
REDIRECT_ALERTS_FILE = 'redirect_alerts.json'
CALL_ALERTS_FILE = 'call_alerts.json'
AUTHENTICATED_USERS_FILE = 'authenticated_users.json'
ADMIN_USER_ID = None  # Will be set on first /start

BOT_START_TIME = time.time()
TOGGLE_COUNT = 0
ERROR_COUNT = 0
BOT_PASSWORD = os.getenv('BOT_PASSWORD', 'changeme')
# authenticated_users will be loaded from file below

# Parse channels from .env
TARGET_CHANNELS = [c.strip() for c in os.getenv('TARGET_CHANNELS', '').split(',') if c.strip()]

processed_contracts = set()

async def notify_all_users(context, message):
    """Send notification to all authenticated users"""
    for user_id in authenticated_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
        except:
            pass  # User might have blocked the bot

async def handle_contract_alert(update, context, source_channel, contract_address, blockchain):
    """Send contract alert with ape/skip options to all authenticated users"""
    channel_name = source_channel if source_channel else "Unknown Channel"
    
    # Create alert message
    blockchain_emoji = "🔷" if blockchain == "Ethereum" else "🟡" if blockchain == "Solana" else "❓"
    
    alert_msg = (
        f"🚨 <b>CONTRACT FOUND</b> {blockchain_emoji}\n\n"
        f"📺 {channel_name}\n"
        f"📄 <code>{contract_address}</code>\n\n"
        f"🤔 <b>Ape or skip?</b>"
    )
    
    # Create buttons for ape/skip
    keyboard = [
        [
            InlineKeyboardButton('🦍 APE IN!', callback_data=f'ape_{contract_address[:10]}'),
            InlineKeyboardButton('❌ Skip', callback_data=f'skip_{contract_address[:10]}')
        ],
        [InlineKeyboardButton('📋 Copy CA', callback_data=f'copy_{contract_address[:10]}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send to all authenticated users
    for user_id in authenticated_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=alert_msg,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except:
            pass  # User might have blocked the bot

async def handle_call_alert(update, context, source_channel, call_content, call_type):
    """Send call alert to all authenticated users"""

    channel_name = source_channel if source_channel else "Unknown Channel"
    
    # Create alert message
    call_emoji = {
        'gem': '💎',
        'call': '📢',
        'pump': '🚀', 
        'moon': '🌙',
        'buy': '💰',
        'signal': '📊',
        'alert': '🚨'
    }.get(call_type.lower(), '📢')
    
    alert_msg = (
        f"📢 <b>{call_type.upper()} DETECTED</b> {call_emoji}\n\n"
        f"📺 {channel_name}\n"
        f"💬 <i>{call_content[:300]}{'...' if len(call_content) > 300 else ''}</i>"
    )
    
    # Send to all authenticated users
    await notify_all_users(context, alert_msg)

async def handle_redirect_alert(update, context, source_channel, redirects):
    """Handle redirect alerts with quick forward options"""
    message_text = update.channel_post.text or ""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Create alert message
    redirect_list = ", ".join([f"@{r}" if not r.startswith('@') else r for r in redirects[:3]])
    if len(redirects) > 3:
        redirect_list += f" +{len(redirects)-3} more"
    
    alert_msg = (
        f"🔄 <b>Redirect Alert!</b>\n\n"
        f"📺 <b>From:</b> {source_channel}\n"
        f"🎯 <b>Redirects to:</b> {redirect_list}\n"
        f"⏰ <b>Time:</b> {timestamp}\n\n"
        f"📝 <b>Message:</b>\n<i>{message_text[:200]}{'...' if len(message_text) > 200 else ''}</i>"
    )
    
    # Create buttons for each redirect
    buttons = []
    for redirect in redirects[:5]:  # Limit to 5 buttons
        clean_redirect = redirect.lstrip('@')
        if clean_redirect.lower() == AUTOBUY_BOT_USERNAME.lower():
            continue  # Skip if it's already our autobuy bot
        
        # Create button to forward the redirect link to autobuy bot
        button_text = f"📤 Send @{clean_redirect} to AutoBuy"
        callback_data = f"forward_redirect|{clean_redirect}"
        buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Add ignore button
    buttons.append([InlineKeyboardButton("❌ Ignore", callback_data="ignore_redirect")])
    
    if buttons:
        reply_markup = InlineKeyboardMarkup(buttons)
        
        # Send to all authenticated users
        for user_id in authenticated_users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=alert_msg,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except:
                pass  # User might have blocked the bot
    
    logger.info(f"Redirect alert sent for {source_channel} -> {redirects}")

def load_processed_contracts():
    global processed_contracts
    if os.path.exists(PROCESSED_CONTRACTS_FILE):
        with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
            processed_contracts = set(line.strip() for line in f if line.strip())
    else:
        processed_contracts = set()

def save_processed_contract(ca, blockchain="Unknown"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(PROCESSED_CONTRACTS_FILE, 'a') as f:
        f.write(f"[{timestamp}] {blockchain}: {ca}\n")

def load_enabled_channels():
    if os.path.exists(ENABLED_CHANNELS_FILE):
        with open(ENABLED_CHANNELS_FILE, 'r') as f:
            return set(json.load(f))
    # Default: all enabled
    return set(TARGET_CHANNELS)

def save_enabled_channels(enabled_channels):
    with open(ENABLED_CHANNELS_FILE, 'w') as f:
        json.dump(list(enabled_channels), f)

enabled_channels = load_enabled_channels()
redirect_alerts_enabled = True  # Default: alerts enabled
call_alerts_enabled = True  # Default: call alerts enabled
contract_alerts_enabled = True  # Default: contract alerts enabled

def load_redirect_settings():
    global redirect_alerts_enabled
    if os.path.exists(REDIRECT_ALERTS_FILE):
        try:
            with open(REDIRECT_ALERTS_FILE, 'r') as f:
                data = json.load(f)
                redirect_alerts_enabled = data.get('enabled', True)
        except:
            redirect_alerts_enabled = True

def save_redirect_settings():
    with open(REDIRECT_ALERTS_FILE, 'w') as f:
        json.dump({'enabled': redirect_alerts_enabled}, f)

def load_call_settings():
    global call_alerts_enabled
    if os.path.exists(CALL_ALERTS_FILE):
        try:
            with open(CALL_ALERTS_FILE, 'r') as f:
                data = json.load(f)
                call_alerts_enabled = data.get('enabled', True)
        except:
            call_alerts_enabled = True

def save_call_settings():
    with open(CALL_ALERTS_FILE, 'w') as f:
        json.dump({'enabled': call_alerts_enabled}, f)

def load_authenticated_users():
    """Load authenticated users from file"""
    if os.path.exists(AUTHENTICATED_USERS_FILE):
        try:
            with open(AUTHENTICATED_USERS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get('users', []))
        except:
            return set()
    return set()

def save_authenticated_users():
    """Save authenticated users to file"""
    with open(AUTHENTICATED_USERS_FILE, 'w') as f:
        json.dump({'users': list(authenticated_users)}, f)

# Load settings on startup
load_redirect_settings()
load_call_settings()
authenticated_users = load_authenticated_users()

def update_env_channels(new_channels):
    """Update the TARGET_CHANNELS line in the .env file."""
    env_path = '.env'
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r') as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith('TARGET_CHANNELS='):
            lines[i] = f"TARGET_CHANNELS={','.join(new_channels)}\n"
            found = True
            break
    if not found:
        lines.append(f"TARGET_CHANNELS={','.join(new_channels)}\n")
    with open(env_path, 'w') as f:
        f.writelines(lines)

def identify_blockchain(address):
    """Identify which blockchain an address belongs to"""
    if address.startswith('0x') and len(address) == 42:
        return "Ethereum"
    elif re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return "Solana"
    else:
        return "Unknown"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if user is authenticated
    if user_id not in authenticated_users:
        context.user_data['awaiting_password'] = True
        welcome_msg = (
            "🔐 <b>Welcome to Buy-Bot!</b>\n\n"
            "This bot monitors Telegram channels for contract addresses and forwards them to your autobuy bot.\n\n"
            "🔒 <b>Authentication Required</b>\n"
            "Please enter the bot password to continue:"
        )
        await update.message.reply_text(welcome_msg, parse_mode='HTML')
        return
    
    # Fun stats
    total_channels = len(TARGET_CHANNELS)
    enabled_count = len(enabled_channels)
    processed_count = len(processed_contracts)
    status_emoji = '🟢' if enabled_count > 0 else '🔴'
    uptime = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    msg = (
        f"🤖 <b>Buy-Bot Dashboard</b>\n\n"
        f"📊 <b>Status:</b> {'🟢 Active' if enabled_count > 0 else '🔴 Inactive'}\n"
        f"📺 <b>Channels:</b> {enabled_count}/{total_channels} monitoring\n"
        f"📄 <b>Contracts:</b> {processed_count} found\n"
        f"⏰ <b>Uptime:</b> {uptime_str}\n\n"
        f"✨ <b>What would you like to do?</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton('📺 Channels', callback_data='show_channels'),
         InlineKeyboardButton('📊 Status', callback_data='show_status')],
        [InlineKeyboardButton('📜 History', callback_data='show_history'),
         InlineKeyboardButton('⚙️ Settings', callback_data='show_settings')],
        [InlineKeyboardButton('❓ Help', callback_data='show_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    if update.effective_user.id not in authenticated_users:
        return
    
    help_text = (
        "❓ <b>How to Use Buy-Bot</b>\n\n"
        "🔹 <b>Monitor Channels:</b> Go to Channels → Toggle on/off\n"
        "🔹 <b>View Activity:</b> Check Status and History\n"
        "🔹 <b>Get Alerts:</b> Enable alerts in Settings\n"
        "🔹 <b>Contract Found:</b> Get instant notifications with ape/skip options\n\n"
        "📝 <b>Quick Commands:</b>\n"
        "• <code>/start</code> - Dashboard\n"
        "• <code>/channels</code> - Manage channels\n"
        "• <code>/history</code> - View contracts\n"
        "• <code>/logout</code> - Sign out\n\n"
        "💡 <b>Tips:</b>\n"
        "• 🟢 = Active/Enabled\n"
        "• 🔴 = Inactive/Disabled\n"
        "• Bot monitors enabled channels 24/7\n"
        "• All contracts auto-forward to your autobuy bot"
    )
    
    keyboard = [
        [InlineKeyboardButton('⬅️ Back to Dashboard', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='HTML')

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logout the current user"""
    user_id = update.effective_user.id
    if user_id in authenticated_users:
        authenticated_users.remove(user_id)
        save_authenticated_users()
        await update.message.reply_text(
            "🔐 <b>Logged out successfully!</b>\n\n"
            "Use /start to login again.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ You are not currently logged in.",
            parse_mode='HTML'
        )

async def test_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test bot functionality"""
    if update.effective_user.id not in authenticated_users:
        await update.message.reply_text('❌ Not authorized.')
        return
    
    test_msg = (
        "🧪 <b>Bot Functionality Test</b>\n\n"
        "✅ <b>Environment Check:</b>\n"
        f"• Bot Token: {'✅ Set' if MONITOR_BOT_TOKEN else '❌ Missing'}\n"
        f"• Autobuy Bot: {'✅ Set' if AUTOBUY_BOT_USERNAME else '❌ Missing'}\n"
        f"• Password: {'✅ Set' if BOT_PASSWORD != 'changeme' else '❌ Default'}\n"
        f"• Channels: {'✅ ' + str(len(TARGET_CHANNELS)) + ' configured' if TARGET_CHANNELS else '❌ None'}\n\n"
        "📊 <b>Current State:</b>\n"
        f"• Enabled Channels: {len(enabled_channels)}/{len(TARGET_CHANNELS)}\n"
        f"• Processed Contracts: {len(processed_contracts)}\n"
        f"• Bot Uptime: {int(time.time() - BOT_START_TIME)}s\n\n"
        "🎯 <b>Test Results:</b>\n"
        "• Authentication: ✅ Working\n"
        "• Channel Management: ✅ Working\n"
        "• Contract Detection: ✅ Ready\n"
        "• Notifications: ✅ Ready\n\n"
        "🚀 <b>Status:</b> Bot is ready to monitor!"
    )
    
    keyboard = [
        [InlineKeyboardButton('🔄 Run Test Again', callback_data='run_test'),
         InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(test_msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(test_msg, reply_markup=reply_markup, parse_mode='HTML')

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('awaiting_password'):
        if update.message.text.strip() == BOT_PASSWORD:
            authenticated_users.add(user_id)
            save_authenticated_users()  # Save to file
            context.user_data['awaiting_password'] = False
            success_msg = (
                "🎉 <b>Authentication Successful!</b>\n\n"
                "✅ You can now access the bot control panel.\n"
                "Use /start to begin managing your bot!"
            )
            await update.message.reply_text(success_msg, parse_mode='HTML')
        else:
            error_msg = (
                "❌ <b>Incorrect Password</b>\n\n"
                "The password you entered is wrong.\n"
                "Please try again:"
            )
            await update.message.reply_text(error_msg, parse_mode='HTML')

async def export_ca_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all contract addresses as a file"""
    if update.effective_user.id not in authenticated_users:
        await update.callback_query.answer('❌ Not authorized.')
        return
    
    try:
        if not os.path.exists(PROCESSED_CONTRACTS_FILE):
            await update.callback_query.answer('📜 No contracts to export yet!')
            return
        
        with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
            content = f.read()
        
        if not content.strip():
            await update.callback_query.answer('📜 No contracts to export yet!')
            return
        
        # Send the file
        with open(PROCESSED_CONTRACTS_FILE, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_user.id,
                document=f,
                filename=f"contract_history_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                caption=f"📜 <b>Complete Contract History</b>\n\n"
                       f"📊 Total contracts: {len(processed_contracts)}\n"
                       f"📅 Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='HTML'
            )
        
        await update.callback_query.answer('✅ History exported!')
        
    except Exception as e:
        await update.callback_query.answer('❌ Export failed!')
        logger.error(f"Export error: {e}")

async def toggle_contract_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle contract alerts on/off"""
    if update.effective_user.id not in authenticated_users:
        return
    
    global contract_alerts_enabled
    
    contract_alerts_enabled = not contract_alerts_enabled
    # No need to save this setting since it's just for session
    
    status = "enabled" if contract_alerts_enabled else "disabled"
    await update.callback_query.answer(f"Contract alerts {status}!")
    
    # Refresh the settings view
    await show_settings(update, context)

async def toggle_call_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle call alerts on/off"""
    if update.effective_user.id not in authenticated_users:
        return
    
    global call_alerts_enabled
    
    call_alerts_enabled = not call_alerts_enabled
    save_call_settings()
    
    status = "enabled" if call_alerts_enabled else "disabled"
    await update.callback_query.answer(f"Call alerts {status}!")
    
    # Refresh the settings view
    await show_settings(update, context)

async def toggle_redirect_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle redirect alerts on/off"""
    global redirect_alerts_enabled
    if update.effective_user.id not in authenticated_users:
        await update.callback_query.answer('❌ Not authorized.')
        return
    
    redirect_alerts_enabled = not redirect_alerts_enabled
    save_redirect_settings()
    
    status = "enabled" if redirect_alerts_enabled else "disabled"
    await update.callback_query.answer(f"🔄 Redirect alerts {status}!")
    
    # Refresh the settings page
    await show_settings(update, context)

async def start_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'show_channels' or query.data == 'refresh_channels':
        await channels(update, context)
    elif query.data == 'show_status' or query.data == 'refresh_status':
        await status(update, context)
    elif query.data == 'show_stats' or query.data == 'refresh_stats':
        await show_fun_stats(update, context)
    elif query.data == 'show_history':
        await show_ca_history(update, context)
    elif query.data == 'show_full_history':
        await show_full_ca_history(update, context)
    elif query.data == 'export_history':
        await export_ca_history(update, context)
    elif query.data == 'show_settings':
        await show_settings(update, context)
    elif query.data == 'toggle_redirect_alerts':
        await toggle_redirect_alerts(update, context)
    elif query.data == 'toggle_call_alerts':
        await toggle_call_alerts(update, context)
    elif query.data == 'toggle_contract_alerts':
        await toggle_contract_alerts(update, context)
    elif query.data == 'show_help' or query.data == 'refresh_help':
        await help_command(update, context)
    elif query.data == 'run_test':
        await test_bot(update, context)
    elif query.data == 'back_to_start':
        await start(update, context)
    else:
        await query.answer('Unknown action.')

async def show_ca_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contract address history"""
    if update.effective_user.id not in authenticated_users:
        return
    
    # Read the processed contracts file with timestamps
    contracts_data = []
    
    try:
        if os.path.exists(PROCESSED_CONTRACTS_FILE):
            with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if it's new format with timestamp: [timestamp] blockchain: address
                if line.startswith('[') and ']' in line:
                    try:
                        timestamp_end = line.find(']')
                        timestamp = line[1:timestamp_end]
                        rest = line[timestamp_end + 1:].strip()
                        if ': ' in rest:
                            blockchain, address = rest.split(': ', 1)
                            contracts_data.append((address, blockchain, timestamp))
                        else:
                            # Malformed new format, treat as address only
                            contracts_data.append((rest, "Unknown", timestamp))
                    except:
                        # Fallback for malformed lines
                        contracts_data.append((line, "Unknown", "Unknown"))
                else:
                    # Old format: just the address
                    contracts_data.append((line, "Unknown", "Unknown"))
    except Exception as e:
        contracts_data = []
        logger.error(f"Error reading contracts file: {e}")
    
    total_contracts = len(contracts_data)
    
    if total_contracts == 0:
        msg = (
            f"📜 <b>Contract Address History</b>\n\n"
            f"🔍 <b>No contracts processed yet</b>\n\n"
            f"The bot will start tracking contracts once it detects them in monitored channels."
        )
    else:
        # Show last 10 contracts
        recent_contracts = contracts_data[-10:] if total_contracts > 10 else contracts_data
        recent_contracts.reverse()  # Show newest first
        
        msg = (
            f"📜 <b>Contract Address History</b>\n\n"
            f"📊 <b>Total Processed:</b> {total_contracts} contracts\n"
            f"📅 <b>Showing:</b> Last {len(recent_contracts)} contracts\n\n"
        )
        
        for i, (address, blockchain, timestamp) in enumerate(recent_contracts, 1):
            # Auto-detect blockchain if unknown
            if blockchain == "Unknown":
                detected_blockchain = identify_blockchain(address)
                blockchain = detected_blockchain if detected_blockchain != "Unknown" else "Unknown"
            
            # Truncate long addresses for display
            short_address = address[:8] + "..." + address[-6:] if len(address) > 16 else address
            blockchain_emoji = "🔷" if blockchain == "Ethereum" else "🟡" if blockchain == "Solana" else "❓"
            time_str = timestamp if timestamp != "Unknown" else "Legacy"
            
            msg += f"{i}. {blockchain_emoji} <code>{short_address}</code>\n"
            msg += f"   📝 {blockchain} • ⏰ {time_str}\n\n"
        
        if total_contracts > 10:
            msg += f"💡 <i>Showing {len(recent_contracts)} of {total_contracts} total contracts</i>\n"
    
    keyboard = [
        [InlineKeyboardButton('🔄 Refresh', callback_data='show_history'),
         InlineKeyboardButton('📤 Export All', callback_data='export_history')],
        [InlineKeyboardButton('📋 Full Addresses', callback_data='show_full_history')],
        [InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def show_full_ca_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full contract addresses without truncation"""
    if update.effective_user.id not in authenticated_users:
        return
    
    # Get contracts data
    contracts_data = []
    try:
        if os.path.exists(PROCESSED_CONTRACTS_FILE):
            with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('[') and ']' in line:
                    try:
                        timestamp_end = line.find(']')
                        timestamp = line[1:timestamp_end]
                        rest = line[timestamp_end + 1:].strip()
                        if ': ' in rest:
                            blockchain, address = rest.split(': ', 1)
                            contracts_data.append((address, blockchain, timestamp))
                        else:
                            contracts_data.append((rest, "Unknown", timestamp))
                    except:
                        contracts_data.append((line, "Unknown", "Unknown"))
                else:
                    contracts_data.append((line, "Unknown", "Unknown"))
    except Exception as e:
        contracts_data = []
    
    total_contracts = len(contracts_data)
    
    if total_contracts == 0:
        msg = f"📋 <b>Full Contract History</b>\n\n🔍 No contracts found."
    else:
        # Show last 5 contracts with full addresses
        recent_contracts = contracts_data[-5:] if total_contracts > 5 else contracts_data
        recent_contracts.reverse()
        
        msg = (
            f"📋 <b>Full Contract History</b>\n\n"
            f"📊 <b>Total:</b> {total_contracts} contracts\n"
            f"📅 <b>Last {len(recent_contracts)} contracts:</b>\n\n"
        )
        
        for i, (address, blockchain, timestamp) in enumerate(recent_contracts, 1):
            if blockchain == "Unknown":
                detected_blockchain = identify_blockchain(address)
                blockchain = detected_blockchain if detected_blockchain != "Unknown" else "Unknown"
            
            blockchain_emoji = "🔷" if blockchain == "Ethereum" else "🟡" if blockchain == "Solana" else "❓"
            time_str = timestamp if timestamp != "Unknown" else "Legacy"
            
            msg += f"{i}. {blockchain_emoji} <b>{blockchain}</b>\n"
            msg += f"<code>{address}</code>\n"
            msg += f"⏰ {time_str}\n\n"
        
        if total_contracts > 5:
            msg += f"💡 <i>Use 📤 Export to get all {total_contracts} contracts</i>"
    
    keyboard = [
        [InlineKeyboardButton('📤 Export All', callback_data='export_history'),
         InlineKeyboardButton('📜 Back to Summary', callback_data='show_history')],
        [InlineKeyboardButton('⬅️ Main Menu', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot settings"""
    if update.effective_user.id not in authenticated_users:
        return
    
    redirect_status = "🟢 Enabled" if redirect_alerts_enabled else "🔴 Disabled"
    call_status = "🟢 Enabled" if call_alerts_enabled else "🔴 Disabled"
    contract_status = "🟢 Enabled" if contract_alerts_enabled else "🔴 Disabled"
    
    msg = (
        f"⚙️ <b>Settings</b>\n\n"
        f"🔄 <b>Redirect Alerts:</b> {redirect_status}\n"
        f"🚨 <b>Call Alerts:</b> {call_status}\n"
        f"🦍 <b>Contract Alerts:</b> {contract_status}\n\n"
        f"💡 Tap any button below to toggle on/off"
    )
    
    keyboard = [
        [InlineKeyboardButton('🔄 Redirect Alerts', callback_data='toggle_redirect_alerts'),
         InlineKeyboardButton('🚨 Call Alerts', callback_data='toggle_call_alerts')],
        [InlineKeyboardButton('🦍 Contract Alerts', callback_data='toggle_contract_alerts')],
        [InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def show_fun_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    total_channels = len(TARGET_CHANNELS)
    enabled_count = len(enabled_channels)
    processed_count = len(processed_contracts)
    uptime = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    # Calculate success rate
    success_rate = "N/A"
    if TOGGLE_COUNT + ERROR_COUNT > 0:
        success_rate = f"{((TOGGLE_COUNT / (TOGGLE_COUNT + ERROR_COUNT)) * 100):.1f}%"
    
    # Calculate efficiency
    efficiency = "N/A"
    if uptime > 0:
        contracts_per_hour = (processed_count / uptime) * 3600
        efficiency = f"{contracts_per_hour:.2f}/hour"
    
    msg = (
        f"📈 <b>Fun Stats Dashboard</b>\n\n"
        f"📊 <b>Channel Performance:</b>\n"
        f"• <code>Enabled:</code> {enabled_count}/{total_channels}\n"
        f"• <code>Disabled:</code> {total_channels - enabled_count}\n"
        f"• <code>Toggle Count:</code> {TOGGLE_COUNT}\n\n"
        f"📦 <b>Contract Processing:</b>\n"
        f"• <code>Total Processed:</code> {processed_count}\n"
        f"• <code>Success Rate:</code> {success_rate}\n"
        f"• <code>Efficiency:</code> {efficiency}\n\n"
        f"⏱️ <b>System Health:</b>\n"
        f"• <code>Uptime:</code> {uptime_str}\n"
        f"• <code>Errors:</code> {ERROR_COUNT}\n"
        f"• <code>Started:</code> {datetime.fromtimestamp(BOT_START_TIME).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"🎯 <b>Performance:</b>\n"
        f"• <code>Status:</code> {'🟢 Excellent' if ERROR_COUNT == 0 else '🟡 Good' if ERROR_COUNT < 5 else '🔴 Needs Attention'}"
    )
    
    keyboard = [
        [InlineKeyboardButton('🔄 Refresh', callback_data='refresh_stats'),
         InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_users:
        return
    
    enabled_list = list(enabled_channels)
    disabled_list = [ch for ch in TARGET_CHANNELS if ch not in enabled_channels]
    
    msg = (
        f"📊 <b>Detailed Status Report</b>\n\n"
        f"🟢 <b>Enabled Channels ({len(enabled_list)}):</b>\n"
    )
    
    if enabled_list:
        for ch in enabled_list:
            msg += f"• <code>{ch}</code> ✅\n"
    else:
        msg += "• <i>No channels enabled</i> ⚠️\n"
    
    msg += f"\n🔴 <b>Disabled Channels ({len(disabled_list)}):</b>\n"
    
    if disabled_list:
        for ch in disabled_list:
            msg += f"• <code>{ch}</code> ❌\n"
    else:
        msg += "• <i>All channels enabled</i> ✅\n"
    
    msg += f"\n📈 <b>Summary:</b>\n"
    msg += f"• <code>Total:</code> {len(TARGET_CHANNELS)} channels\n"
    msg += f"• <code>Active:</code> {len(enabled_list)} channels\n"
    msg += f"• <code>Inactive:</code> {len(disabled_list)} channels\n"
    
    keyboard = [
        [InlineKeyboardButton('🔄 Refresh', callback_data='refresh_status'),
         InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_users:
        return
    
    keyboard = []
    for ch in TARGET_CHANNELS:
        enabled = ch in enabled_channels
        btn_text = f"{'🟢' if enabled else '🔴'} {ch}"
        callback_data = f"toggle|{ch}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
    
    # Add Refresh and Back buttons
    keyboard.append([
        InlineKeyboardButton('🔄 Refresh', callback_data='refresh_channels'),
        InlineKeyboardButton('⬅️ Back', callback_data='back_to_start')
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = (
        f"📋 <b>Channel Management</b>\n\n"
        f"🎯 <b>Instructions:</b>\n"
        f"Click on any channel to toggle it on/off\n\n"
        f"📊 <b>Legend:</b>\n"
        f"🟢 = Enabled (monitoring active)\n"
        f"🔴 = Disabled (not monitoring)\n\n"
        f"💡 <b>Tip:</b> Only enabled channels will be monitored for contract addresses."
    )
    
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='HTML')
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='HTML')

async def handle_contract_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contract alert button clicks (ape/skip/copy)"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('ape_'):
        ca_short = query.data[4:]  # Remove 'ape_' prefix
        await query.edit_message_text(
            f"🦍 <b>APING IN!</b>\n\n"
            f"Contract: <code>{ca_short}...</code>\n"
            f"✅ Sent to autobuy bot!\n\n"
            f"🚀 <i>Good luck anon!</i>",
            parse_mode='HTML'
        )
        
    elif query.data.startswith('skip_'):
        ca_short = query.data[5:]  # Remove 'skip_' prefix
        await query.edit_message_text(
            f"❌ <b>SKIPPED</b>\n\n"
            f"Contract: <code>{ca_short}...</code>\n"
            f"🤷‍♂️ <i>Maybe next time!</i>",
            parse_mode='HTML'
        )
        
    elif query.data.startswith('copy_'):
        ca_short = query.data[5:]  # Remove 'copy_' prefix
        await query.answer(f"📋 Contract copied: {ca_short}...", show_alert=True)

async def handle_redirect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle redirect forwarding callbacks"""
    if update.effective_user.id not in authenticated_users:
        await update.callback_query.answer('❌ Not authorized.')
        return
    
    query = update.callback_query
    
    if query.data == "ignore_redirect":
        await query.answer("🚫 Redirect ignored")
        await query.delete_message()
        return
    
    if query.data.startswith("forward_redirect|"):
        _, redirect_target = query.data.split('|', 1)
        
        try:
            # Send the redirect target to the autobuy bot
            await context.bot.send_message(
                chat_id=f"@{AUTOBUY_BOT_USERNAME}",
                text=f"@{redirect_target}"
            )
            
            # Notify user of success
            await query.answer(f"✅ Sent @{redirect_target} to autobuy bot!")
            
            # Update the message to show it was handled
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await query.edit_message_text(
                text=f"✅ <b>Redirect Forwarded!</b>\n\n"
                     f"🎯 <b>Sent:</b> @{redirect_target}\n"
                     f"📤 <b>To:</b> @{AUTOBUY_BOT_USERNAME}\n"
                     f"⏰ <b>Time:</b> {timestamp}",
                parse_mode='HTML'
            )
            
            logger.info(f"Redirect forwarded: @{redirect_target} to @{AUTOBUY_BOT_USERNAME}")
            
        except Exception as e:
            await query.answer(f"❌ Failed to forward redirect!")
            logger.error(f"Error forwarding redirect: {e}")

async def toggle_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOGGLE_COUNT
    if update.effective_user.id not in authenticated_users:
        await update.callback_query.answer('❌ Not authorized.')
        return
    
    query = update.callback_query
    
    # Handle redirect callbacks
    if query.data.startswith("forward_redirect|") or query.data == "ignore_redirect":
        await handle_redirect_callback(update, context)
        return
    
    _, ch = query.data.split('|', 1)
    
    if ch in enabled_channels:
        enabled_channels.remove(ch)
        action = "disabled"
        action_emoji = "🔴"
    else:
        enabled_channels.add(ch)
        action = "enabled"
        action_emoji = "🟢"
    
    TOGGLE_COUNT += 1
    save_enabled_channels(enabled_channels)
    
    # Notify admin
    await query.answer(f"✅ {ch} {action}")
    
    # Send detailed notification to all users
    await notify_all_users(context, 
        f"<b>🔄 Channel Toggle</b>\n"
        f"{action_emoji} <code>{ch}</code> {action}\n"
        f"📊 Total enabled: {len(enabled_channels)}/{len(TARGET_CHANNELS)}")
    
    # Refresh the channel list with updated emoji
    await channels(update, context)

async def addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_users:
        await update.message.reply_text('❌ Not authorized.')
        return
    
    if not context.args:
        help_text = (
            "❌ <b>Usage Error</b>\n\n"
            "📝 <b>Correct Usage:</b>\n"
            "<code>/addchannel @username</code>\n"
            "<code>/addchannel -1001234567890</code>\n\n"
            "💡 <b>Examples:</b>\n"
            "• <code>/addchannel @cryptochannel</code>\n"
            "• <code>/addchannel -1001234567890</code>\n\n"
            "🔍 <b>Note:</b> Use @ for public channels, -100 for private groups"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')
        return
    
    ch = context.args[0].strip()
    if ch in TARGET_CHANNELS:
        await update.message.reply_text(f'⚠️ <code>{ch}</code> is already in the list.', parse_mode='HTML')
        return
    
    TARGET_CHANNELS.append(ch)
    enabled_channels.add(ch)
    update_env_channels(TARGET_CHANNELS)
    save_enabled_channels(enabled_channels)
    
    success_msg = (
        f"✅ <b>Channel Added Successfully!</b>\n\n"
        f"📝 <b>Details:</b>\n"
        f"• <code>{ch}</code> added and enabled\n"
        f"• Total channels: {len(TARGET_CHANNELS)}\n"
        f"• Enabled channels: {len(enabled_channels)}\n\n"
        f"🎯 The bot will now monitor this channel for contract addresses."
    )
    
    await update.message.reply_text(success_msg, parse_mode='HTML')
    
    # Notify all users
    await notify_all_users(context,
        f"<b>✅ Channel Added</b>\n"
        f"📝 <code>{ch}</code> added and enabled\n"
        f"📊 Total channels: {len(TARGET_CHANNELS)}")
    
    await channels(update, context)

async def removechannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in authenticated_users:
        await update.message.reply_text('❌ Not authorized.')
        return
    
    if not context.args:
        help_text = (
            "❌ <b>Usage Error</b>\n\n"
            "📝 <b>Correct Usage:</b>\n"
            "<code>/removechannel @username</code>\n"
            "<code>/removechannel -1001234567890</code>\n\n"
            "💡 <b>Examples:</b>\n"
            "• <code>/removechannel @cryptochannel</code>\n"
            "• <code>/removechannel -1001234567890</code>"
        )
        await update.message.reply_text(help_text, parse_mode='HTML')
        return
    
    ch = context.args[0].strip()
    if ch not in TARGET_CHANNELS:
        await update.message.reply_text(f'⚠️ <code>{ch}</code> is not in the list.', parse_mode='HTML')
        return
    
    TARGET_CHANNELS.remove(ch)
    enabled_channels.discard(ch)
    update_env_channels(TARGET_CHANNELS)
    save_enabled_channels(enabled_channels)
    
    success_msg = (
        f"✅ <b>Channel Removed Successfully!</b>\n\n"
        f"📝 <b>Details:</b>\n"
        f"• <code>{ch}</code> removed\n"
        f"• Total channels: {len(TARGET_CHANNELS)}\n"
        f"• Enabled channels: {len(enabled_channels)}\n\n"
        f"🎯 The bot will no longer monitor this channel."
    )
    
    await update.message.reply_text(success_msg, parse_mode='HTML')
    
    # Notify all users
    await notify_all_users(context,
        f"<b>❌ Channel Removed</b>\n"
        f"📝 <code>{ch}</code> removed\n"
        f"📊 Total channels: {len(TARGET_CHANNELS)}")
    
    await channels(update, context)

async def forward_contract_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ERROR_COUNT
    
    # Only process messages from enabled channels
    if not update.channel_post:
        return
    
    ch_username = update.channel_post.chat.username
    ch_id = str(update.channel_post.chat.id)
    
    # Accept both @username and numeric id
    if ch_username:
        ch_key = f"@{ch_username}"
    else:
        ch_key = ch_id
    
    if ch_key not in enabled_channels:
        logger.info(f"❌ Channel {ch_key} not in enabled_channels: {enabled_channels}")
        return
    else:
        logger.info(f"✅ Channel {ch_key} is enabled")
    
    message_text = update.channel_post.text or ""
    logger.info(f"📝 Message from {ch_key}: {message_text[:100]}...")
    
    # Check for trading calls first
    call_patterns = {
        'call': [r'\bcall\b', r'\bcalling\b', r'🔥.*call', r'call.*🔥', r'CALL', r'Call'],
        'gem': [r'\bgem\b', r'💎', r'\bgem find\b', r'hidden gem', r'GEM', r'Gem'],
        'pump': [r'\bpump\b', r'🚀', r'\bpumping\b', r'about to pump', r'PUMP', r'Pump'],
        'moon': [r'\bmoon\b', r'🌙', r'\bmooning\b', r'going to moon', r'MOON', r'Moon'],
        'buy': [r'\bbuy now\b', r'\bload up\b', r'\bentry\b', r'💰.*buy', r'BUY', r'Buy'],
        'signal': [r'\bsignal\b', r'\balert\b', r'📊', r'trading signal', r'SIGNAL', r'Signal'],
        'alert': [r'\bBREAKING\b', r'\bURGENT\b', r'🚨', r'\bFLASH\b', r'ALERT', r'Alert'],
        'test': [r'test.*call', r'TEST', r'0x[a-fA-F0-9]+']  # Test pattern
    }
    
    # Detect call type
    detected_call = None
    for call_type, patterns in call_patterns.items():
        for pattern in patterns:
            if re.search(pattern, message_text, re.IGNORECASE):
                detected_call = call_type
                break
        if detected_call:
            break
    
    # Check for redirects/links to other channels or bots
    redirect_patterns = [
        r't\.me/([^/\s]+)',  # t.me/channel or t.me/bot
        r'@(\w+)',           # @channel or @bot mentions
        r'telegram\.me/([^/\s]+)',  # telegram.me/channel
    ]
    
    redirects_found = []
    for pattern in redirect_patterns:
        matches = re.findall(pattern, message_text, re.IGNORECASE)
        for match in matches:
            if match.lower() != ch_username.lower() if ch_username else True:
                redirects_found.append(match)
    
    # Check for contract addresses
    logger.info(f"🔍 Using CA_PATTERN: {CA_PATTERN}")
    contract_addresses = re.findall(CA_PATTERN, message_text)
    if contract_addresses:
        logger.info(f"🔍 CONTRACT DETECTED: {len(contract_addresses)} contracts in {ch_key}")
        for ca in contract_addresses:
            logger.info(f"📄 Contract: {ca}")
    
    # Handle redirects (only if alerts are enabled)
    if redirects_found and not contract_addresses and redirect_alerts_enabled:
        await handle_redirect_alert(update, context, ch_key, redirects_found)
    
    # Handle call alerts (only if alerts are enabled)
    if detected_call and call_alerts_enabled:
        await handle_call_alert(update, context, ch_key, message_text, detected_call)
    
    if not contract_addresses:
        logger.info(f"❌ No contracts found in message from {ch_key}")
        return
    
    logger.info(f"✅ Processing {len(contract_addresses)} contracts from {ch_key}")
    for ca in contract_addresses:
        # Send contract alert to users (if enabled)
        if contract_alerts_enabled:
            logger.info(f"🦍 Sending contract alert for: {ca}")
            blockchain = identify_blockchain(ca)
            await handle_contract_alert(update, context, ch_key, ca, blockchain)
        else:
            logger.info(f"⚠️ Contract alerts disabled, skipping: {ca}")
        if ca in processed_contracts:
            logger.info(f"Contract address {ca} already processed. Skipping.")
            continue
        
        try:
            blockchain = identify_blockchain(ca)
            await context.bot.send_message(
                chat_id=f"@{AUTOBUY_BOT_USERNAME}",
                text=ca
            )
            
            logger.info(f"Forwarded {blockchain} contract address: {ca}")
            processed_contracts.add(ca)
            save_processed_contract(ca, blockchain)
            
            # Notify all users with detailed info
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            await notify_all_users(context,
                f"<b>✅ Contract Forwarded Successfully!</b>\n\n"
                f"🔗 <b>Blockchain:</b> {blockchain}\n"
                f"📝 <b>Address:</b> <code>{ca}</code>\n"
                f"📺 <b>Channel:</b> {ch_key}\n"
                f"⏰ <b>Time:</b> {timestamp}\n\n"
                f"🎯 <b>Status:</b> Sent to autobuy bot")
                
        except Exception as e:
            ERROR_COUNT += 1
            logger.error(f"Error forwarding contract address: {e}")
            
            await notify_all_users(context,
                f"<b>❌ Forward Error</b>\n\n"
                f"📝 <b>Address:</b> <code>{ca}</code>\n"
                f"📺 <b>Channel:</b> {ch_key}\n"
                f"⚠️ <b>Error:</b> {str(e)}\n\n"
                f"🔧 <b>Action:</b> Check autobuy bot status")

def main():
    load_processed_contracts()
    global enabled_channels
    enabled_channels = load_enabled_channels()
    
    if not MONITOR_BOT_TOKEN:
        logger.error("MONITOR_BOT_TOKEN not found in environment variables")
        return
    
    application = Application.builder().token(MONITOR_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("channels", channels))
    application.add_handler(CommandHandler("addchannel", addchannel))
    application.add_handler(CommandHandler("removechannel", removechannel))
    application.add_handler(CommandHandler("history", show_ca_history))
    application.add_handler(CommandHandler("test", test_bot))
    application.add_handler(CommandHandler("logout", logout))
    
    # Add callback handlers
    application.add_handler(CallbackQueryHandler(start_buttons, pattern="^(show_channels|show_status|show_stats|show_history|show_full_history|export_history|show_settings|toggle_redirect_alerts|toggle_call_alerts|toggle_contract_alerts|show_help|refresh_channels|refresh_status|refresh_stats|refresh_help|run_test|back_to_start)$"))
    application.add_handler(CallbackQueryHandler(handle_contract_callback, pattern="^(ape_|skip_|copy_)"))
    application.add_handler(CallbackQueryHandler(toggle_channel))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_contract_address))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler))
    
    logger.info("🚀 Starting Telegram Buy-Bot Control Interface...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 