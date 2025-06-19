import os
import re
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest
import colorama
from colorama import Fore, Back, Style

# Initialize colorama
colorama.init()

# Load environment variables
load_dotenv()

# Configure logging with colors
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    grey = Fore.WHITE
    blue = Fore.CYAN
    yellow = Fore.YELLOW
    red = Fore.RED
    bold_red = Fore.RED + Style.BRIGHT
    reset = Style.RESET_ALL

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

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print a fancy banner"""
    clear_screen()
    channels = get_target_channels()
    channels_text = "\n    ║  ".join([f"Monitoring: {channel}" for channel in channels])
    
    banner = f"""
    {Fore.CYAN}╔══════════════════════════════════════════╗
    ║      {Fore.GREEN}Telegram Contract Monitor{Fore.CYAN}       ║
    ║                                          ║
    ║  {channels_text}
    ║  Forwarding to: @{os.getenv('AUTOBUY_BOT_USERNAME')}
    ╚══════════════════════════════════════════╝{Style.RESET_ALL}
    """
    print(banner)

def print_menu():
    """Print the main menu"""
    menu = f"""
    {Fore.YELLOW}📋 Available Commands:{Style.RESET_ALL}
    {Fore.CYAN}---------------------
    {Fore.GREEN}1. /start{Style.RESET_ALL} - Check if bot is running
    {Fore.GREEN}2. /status{Style.RESET_ALL} - Show current status
    {Fore.GREEN}3. /help{Style.RESET_ALL} - Show this menu
    {Fore.GREEN}4. Ctrl+C{Style.RESET_ALL} - Stop the bot

    {Fore.YELLOW}💡 Tips:{Style.RESET_ALL}
    {Fore.CYAN}- The bot will automatically forward any contract addresses it finds
    - You'll see real-time updates in this window
    - Check the logs above for activity{Style.RESET_ALL}
    """
    print(menu)

def print_status(message, status_type="info"):
    """Print a status message with color"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status_type == "info":
        print(f"{Fore.CYAN}[{timestamp}] ℹ️ {message}{Style.RESET_ALL}")
    elif status_type == "success":
        print(f"{Fore.GREEN}[{timestamp}] ✅ {message}{Style.RESET_ALL}")
    elif status_type == "error":
        print(f"{Fore.RED}[{timestamp}] ❌ {message}{Style.RESET_ALL}")
    elif status_type == "warning":
        print(f"{Fore.YELLOW}[{timestamp}] ⚠️ {message}{Style.RESET_ALL}")

def get_target_channels():
    """Get list of target channels from environment variable."""
    channels = os.getenv('TARGET_CHANNELS', '').split(',')
    return [channel.strip() for channel in channels if channel.strip()]

def check_environment():
    """Check if all required environment variables are set."""
    print_status("Checking configuration...", "info")
    required_vars = ['API_ID', 'API_HASH', 'AUTOBUY_BOT_USERNAME', 'TARGET_CHANNELS']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print_status("Missing required settings:", "error")
        for var in missing_vars:
            print_status(f"   - {var}", "error")
        print_status("Please check your .env file and make sure all variables are set correctly.", "error")
        return False
    
    # Check if at least one channel is specified
    channels = get_target_channels()
    if not channels:
        print_status("No target channels specified!", "error")
        print_status("Please add at least one channel to TARGET_CHANNELS in your .env file", "error")
        return False
    
    print_status("Configuration check passed!", "success")
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

        print_status(f"Received message from channel: @{channel_username}", "info")
        print_status(f"Message content: {event.message.text}", "info")

        # Check if the message is from any of the target channels
        target_channels = [channel.lstrip('@') for channel in get_target_channels()]
        if channel_username not in target_channels:
            print_status(f"Channel @{channel_username} not in target channels: {target_channels}", "info")
            return

        # Extract contract addresses from the message
        message_text = event.message.text
        contract_addresses = re.findall(os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}'), message_text)

        if not contract_addresses:
            print_status("No contract addresses found in message", "info")
            return

        print_status(f"Found contract addresses: {contract_addresses}", "success")

        # Forward each contract address to the autobuy bot
        for ca in contract_addresses:
            try:
                # Send the contract address to the autobuy bot
                await event.client.send_message(
                    os.getenv('AUTOBUY_BOT_USERNAME'),
                    ca
                )
                print_status(f"Forwarded contract address from @{channel_username}: {ca}", "success")
                print(f"\n{Fore.GREEN}🔄 New contract address detected and forwarded!{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📢 Channel: @{channel_username}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}📝 Contract: {ca}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
            except Exception as e:
                print_status(f"Error forwarding contract address from @{channel_username}: {e}", "error")
                print(f"\n{Fore.RED}⚠️ Error forwarding contract address!{Style.RESET_ALL}")
                print(f"{Fore.CYAN}📢 Channel: @{channel_username}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}📝 Contract: {ca}{Style.RESET_ALL}")
                print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")

    except Exception as e:
        print_status(f"Error processing message: {e}", "error")

async def main():
    """Main function to run the client."""
    print_banner()
    print_status("Starting up...", "info")
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    # Get configuration
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = get_target_channels()
    autobuy_bot = os.getenv('AUTOBUY_BOT_USERNAME')
    
    print_status("Initializing client...", "info")
    
    # Create the client
    client = TelegramClient('monitor_session', api_id, api_hash)
    
    # Add event handler for new messages
    client.add_event_handler(handle_new_message, events.NewMessage(chats=target_channels))
    
    print_status("Client is now running!", "success")
    print(f"\n{Fore.CYAN}📢 Monitoring channels:{Style.RESET_ALL}")
    for channel in target_channels:
        print(f"{Fore.GREEN}   • {channel}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🤖 Forwarding to: @{autobuy_bot}{Style.RESET_ALL}")
    
    # Print the menu
    print_menu()
    
    print(f"\n{Fore.CYAN}⏳ Waiting for contract addresses...{Style.RESET_ALL}\n")
    
    try:
        # Start the client
        await client.start()
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}👋 Client stopped by user. Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        print(f"\n{Fore.RED}❌ Client encountered an error and needs to stop.{Style.RESET_ALL}")
        print(f"{Fore.RED}Please check the error message above and try again.{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 