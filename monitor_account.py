import os
import re
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest

# Load environment variables
load_dotenv()

# Configure logging with colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(ch)

def get_target_channels():
    """Get list of target channels from environment variable."""
    channels = os.getenv('TARGET_CHANNELS', '').split(',')
    return [channel.strip() for channel in channels if channel.strip()]

def print_banner():
    """Print a fancy banner"""
    channels = get_target_channels()
    channels_text = "\n    ║  ".join([f"Monitoring: {channel}" for channel in channels])
    
    banner = f"""
    ╔══════════════════════════════════════════╗
    ║      Telegram Contract Monitor Bot       ║
    ║                                          ║
    ║  {channels_text}
    ║  Forwarding to: @{os.getenv('AUTOBUY_BOT_USERNAME')}
    ╚══════════════════════════════════════════╝
    """
    print(banner)

def print_menu():
    """Print the main menu"""
    menu = """
    📋 Available Commands:
    ---------------------
    1. /start - Check if bot is running
    2. /status - Show current status
    3. /help - Show this menu
    4. Ctrl+C - Stop the bot

    💡 Tips:
    - The bot will automatically forward any contract addresses it finds
    - You'll see real-time updates in this window
    - Check the logs above for activity
    """
    print(menu)

def check_environment():
    """Check if all required environment variables are set."""
    print("\n🔍 Checking configuration...")
    required_vars = ['API_ID', 'API_HASH', 'AUTOBUY_BOT_USERNAME', 'TARGET_CHANNELS']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("❌ Missing required settings:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        logger.error("\nPlease check your .env file and make sure all variables are set correctly.")
        return False
    
    # Check if at least one channel is specified
    channels = get_target_channels()
    if not channels:
        logger.error("❌ No target channels specified!")
        logger.error("Please add at least one channel to TARGET_CHANNELS in your .env file")
        return False
    
    print("✅ Configuration check passed!")
    return True

async def handle_new_message(event):
    """Handle new messages and forward contract addresses."""
    try:
        # Get the channel username
        chat = await event.get_chat()
        if not hasattr(chat, 'username'):
            return
        
        channel_username = chat.username
        if not channel_username:
            return

        logger.info(f"Received message from channel: @{channel_username}")
        logger.info(f"Message content: {event.message.text}")

        # Check if the message is from any of the target channels
        target_channels = [channel.lstrip('@') for channel in get_target_channels()]
        if channel_username not in target_channels:
            logger.info(f"Channel @{channel_username} not in target channels: {target_channels}")
            return

        # Extract contract addresses from the message
        message_text = event.message.text
        contract_addresses = re.findall(os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}'), message_text)

        if not contract_addresses:
            logger.info("No contract addresses found in message")
            return

        logger.info(f"Found contract addresses: {contract_addresses}")

        # Forward each contract address to the autobuy bot
        for ca in contract_addresses:
            try:
                # Send the contract address to the autobuy bot
                await event.client.send_message(
                    os.getenv('AUTOBUY_BOT_USERNAME'),
                    ca
                )
                logger.info(f"✅ Forwarded contract address from @{channel_username}: {ca}")
                print(f"\n🔄 New contract address detected and forwarded!")
                print(f"📢 Channel: @{channel_username}")
                print(f"📝 Contract: {ca}")
                print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                logger.error(f"❌ Error forwarding contract address from @{channel_username}: {e}")
                print(f"\n⚠️ Error forwarding contract address!")
                print(f"📢 Channel: @{channel_username}")
                print(f"📝 Contract: {ca}")
                print(f"❌ Error: {str(e)}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")

async def main():
    """Main function to run the client."""
    print_banner()
    print("\n🚀 Starting up...")
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    # Get configuration
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = get_target_channels()
    autobuy_bot = os.getenv('AUTOBUY_BOT_USERNAME')
    
    print("\n🔄 Initializing client...")
    
    # Create the client
    client = TelegramClient('monitor_session', api_id, api_hash)
    
    # Add event handler for new messages
    client.add_event_handler(handle_new_message, events.NewMessage(chats=target_channels))
    
    print("\n✅ Client is now running!")
    print("📢 Monitoring channels:")
    for channel in target_channels:
        print(f"   • {channel}")
    print(f"🤖 Forwarding to: @{autobuy_bot}")
    
    # Print the menu
    print_menu()
    
    print("\n⏳ Waiting for contract addresses...\n")
    
    try:
        # Start the client
        await client.start()
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n\n👋 Client stopped by user. Goodbye!")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print("\n❌ Client encountered an error and needs to stop.")
        print("Please check the error message above and try again.")
        sys.exit(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 