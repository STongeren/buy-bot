#!/usr/bin/env python3
"""
VPS-Optimized Telegram Contract Monitor Bot
Designed for headless server environments
"""

import os
import re
import time
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import PeerIdInvalidError

# Load environment variables
load_dotenv()

# Configure logging for VPS
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/buy-bot/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
processed_contracts = set()
status_data = {
    'start_time': datetime.now(),
    'processed_count': 0,
    'last_contract': '-',
    'last_channel': '-',
    'last_status': '-',
}

def load_processed_contracts():
    """Load processed contract addresses from file."""
    global processed_contracts
    try:
        if os.path.exists('processed_contracts.txt'):
            with open('processed_contracts.txt', 'r') as f:
                processed_contracts = set(line.strip() for line in f if line.strip())
            logger.info(f"Loaded {len(processed_contracts)} processed contracts")
    except Exception as e:
        logger.error(f"Error loading processed contracts: {e}")

def save_processed_contract(ca):
    """Save a processed contract address to file."""
    try:
        with open('processed_contracts.txt', 'a') as f:
            f.write(ca + '\n')
    except Exception as e:
        logger.error(f"Error saving contract: {e}")

def get_target_channels():
    """Get list of target channels from environment."""
    channels = os.getenv('TARGET_CHANNELS', '').split(',')
    return [channel.strip() for channel in channels if channel.strip()]

async def send_notification(client, message):
    """Send notification to configured chat."""
    notify_chat_id = os.getenv('NOTIFY_CHAT_ID')
    if notify_chat_id:
        try:
            await client.send_message(int(notify_chat_id), message)
            logger.info(f"Notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

async def handle_new_message(event):
    """Handle new messages and forward contract addresses."""
    try:
        chat = await event.get_chat()
        if not hasattr(chat, 'username') or not chat.username:
            return
        
        channel_username = chat.username
        target_channels = [channel.lstrip('@') for channel in get_target_channels()]
        
        if channel_username not in target_channels:
            return
        
        logger.info(f"📨 Message from @{channel_username}: {event.message.text[:100]}...")
        
        message_text = event.message.text
        ca_pattern = os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}')
        contract_addresses = re.findall(ca_pattern, message_text)
        
        if not contract_addresses:
            return
        
        logger.info(f"🔍 Found contracts: {contract_addresses}")
        
        for ca in contract_addresses:
            if ca in processed_contracts:
                logger.info(f"⏭️ Skipping duplicate: {ca}")
                status_data['last_status'] = 'Skipped (duplicate)'
                continue
            
            try:
                # Forward to autobuy bot
                await event.client.send_message(
                    os.getenv('AUTOBUY_BOT_USERNAME'),
                    ca
                )
                
                # Update status
                processed_contracts.add(ca)
                save_processed_contract(ca)
                status_data['processed_count'] += 1
                status_data['last_contract'] = ca
                status_data['last_channel'] = channel_username
                status_data['last_status'] = 'Success'
                
                # Log success
                success_msg = f"✅ Forwarded: {ca} from @{channel_username}"
                logger.info(success_msg)
                
                # Send notification
                notify_msg = f"✅ Buy triggered for contract: {ca} from channel @{channel_username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await send_notification(event.client, notify_msg)
                
            except Exception as e:
                error_msg = f"❌ Failed to forward {ca} from @{channel_username}: {e}"
                logger.error(error_msg)
                status_data['last_status'] = 'Failed'
                
                # Send error notification
                notify_msg = f"❌ Failed to buy contract: {ca} from channel @{channel_username}. Error: {str(e)}"
                await send_notification(event.client, notify_msg)
                
    except Exception as e:
        logger.error(f"Error processing message: {e}")

def print_status():
    """Print current bot status."""
    uptime = datetime.now() - status_data['start_time']
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    print("\n" + "="*60)
    print("🤖 Telegram Contract Monitor Bot - VPS Status")
    print("="*60)
    print(f"⏱️  Uptime: {uptime_str}")
    print(f"📊 Processed: {status_data['processed_count']}")
    print(f"📝 Last Contract: {status_data['last_contract']}")
    print(f"📢 Last Channel: {status_data['last_channel']}")
    print(f"🔔 Last Status: {status_data['last_status']}")
    print(f"📡 Monitoring: {', '.join(get_target_channels())}")
    print(f"🎯 Forwarding to: @{os.getenv('AUTOBUY_BOT_USERNAME')}")
    print("="*60)

async def main():
    """Main function."""
    print("🚀 Starting VPS Telegram Contract Monitor Bot...")
    
    # Check environment
    required_vars = ['API_ID', 'API_HASH', 'AUTOBUY_BOT_USERNAME', 'TARGET_CHANNELS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        return
    
    # Load processed contracts
    load_processed_contracts()
    
    # Get configuration
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = get_target_channels()
    
    if not target_channels:
        logger.error("No target channels specified!")
        return
    
    logger.info(f"Monitoring channels: {target_channels}")
    logger.info(f"Forwarding to: @{os.getenv('AUTOBUY_BOT_USERNAME')}")
    
    # Create client
    client = TelegramClient('monitor_session', api_id, api_hash)
    
    try:
        # Start client
        await client.start()
        logger.info("✅ Connected to Telegram")
        
        # Resolve channel entities
        resolved_channels = []
        for channel in target_channels:
            try:
                entity = await client.get_entity(channel)
                resolved_channels.append(entity)
                logger.info(f"✅ Resolved: {channel} -> {entity.title}")
            except Exception as e:
                logger.error(f"❌ Failed to resolve {channel}: {e}")
        
        if not resolved_channels:
            logger.error("No channels could be resolved!")
            return
        
        # Add event handler
        client.add_event_handler(handle_new_message, events.NewMessage(chats=resolved_channels))
        
        logger.info("🤖 Bot is now running and monitoring channels...")
        print_status()
        
        # Keep running
        await client.run_until_disconnected()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1) 