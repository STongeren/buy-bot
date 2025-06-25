import sys
import subprocess
import os
import asyncio
from plyer import notification

def ensure_requirements():
    try:
        import rich
        import colorama
        import telethon
        import dotenv
    except ImportError:
        print("Missing dependencies. Installing requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed. Restarting script...")
        os.execv(sys.executable, [sys.executable] + sys.argv)

ensure_requirements()

import re
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest
import colorama
from colorama import Fore, Back, Style
from telethon.errors.rpcerrorlist import PeerIdInvalidError
import platform
if platform.system() == 'Windows':
    import winsound
    import ctypes
# --- rich imports ---
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.prompt import Prompt
from rich import box

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

console = Console()
activity_feed = []  # List of (timestamp, message, style)
activity_feed_max = 8  # More compact
status_data = {
    'start_time': datetime.now(),
    'processed_count': 0,
    'last_contract': '-',
    'last_channel': '-',
    'last_status': '-',
    'channels': [],
}

# --- Stylish Header ---
def print_header():
    header = Text()
    header.append("\n╔════════════════════════════════════════════╗\n", style="bold cyan")
    header.append("║      ", style="bold cyan")
    header.append("💎 Jacobs Crypto Tools 💎", style="bold magenta")
    header.append("            ║\n", style="bold cyan")
    header.append("╚════════════════════════════════════════════╝\n", style="bold cyan")
    console.print(Align.center(header))
    # Divider
    console.print("[dim]─" * (min(console.width, 50)), justify="center")

def print_banner():
    """Print a fancy banner using rich"""
    channels = get_target_channels()
    status_data['channels'] = channels
    banner_text = Text()
    banner_text.append("\n Telegram Contract Monitor ", style="bold cyan on black")
    banner_text.append("\n" + ("─" * 32) + "\n", style="cyan")
    for channel in channels:
        banner_text.append(f"  Monitoring: {channel}\n", style="green")
    banner_text.append(f"  Forwarding to: @{os.getenv('AUTOBUY_BOT_USERNAME')}\n", style="yellow")
    banner_text.append("─" * 32 + "\n", style="cyan")
    console.print(Panel(banner_text, expand=False, border_style="cyan", title="[bold green]Welcome!"))

def print_menu():
    """Print the main menu using rich"""
    menu = Table(show_header=False, box=box.ROUNDED, expand=False)
    menu.add_row("[bold yellow]📋 Available Commands:")
    menu.add_row("[green]/start[/] - Check if bot is running")
    menu.add_row("[green]/status[/] - Show current status")
    menu.add_row("[green]/last[/] - Show last processed contract")
    menu.add_row("[green]/clear[/] - Clear activity feed")
    menu.add_row("[green]/help[/] - Show this menu")
    menu.add_row("[green]Ctrl+C[/] - Stop the bot")
    menu.add_row("")
    menu.add_row("[yellow]💡 Tips:")
    menu.add_row("[cyan]- The bot will automatically forward any contract addresses it finds")
    menu.add_row("[cyan]- You'll see real-time updates in this window")
    menu.add_row("[cyan]- Check the activity feed below for activity")
    console.print(menu)

def print_status(message, status_type="info"):
    """Add a status message to the activity feed with color."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    style = {
        "info": "cyan",
        "success": "green",
        "error": "red",
        "warning": "yellow"
    }.get(status_type, "white")
    activity_feed.append((timestamp, message, style))
    if len(activity_feed) > activity_feed_max:
        activity_feed.pop(0)

def get_status_panel():
    """Return a rich Panel with live status info and icons."""
    uptime = datetime.now() - status_data['start_time']
    uptime_str = str(timedelta(seconds=int(uptime.total_seconds())))
    table = Table.grid(padding=(0,1), expand=False)
    table.add_column(justify="right", ratio=1)
    table.add_column(justify="left", ratio=2)
    table.add_row("[bold cyan]⏱️ Uptime:", f"[white]{uptime_str}")
    table.add_row("[bold cyan]📡 Channels:", f"[white]{len(status_data['channels'])}")
    table.add_row("[bold cyan]✅ Processed:", f"[white]{status_data['processed_count']}")
    table.add_row("[bold cyan]📝 Last Contract:", f"[yellow]{status_data['last_contract']}")
    table.add_row("[bold cyan]📢 Last Channel:", f"[green]{status_data['last_channel']}")
    table.add_row("[bold cyan]🔔 Last Status:", f"[magenta]{status_data['last_status']}")
    return Panel(table, title="[bold green]Live Status", border_style="bright_cyan", padding=(0,1), width=min(console.width, 80), box=box.ROUNDED)

def get_activity_panel():
    """Return a rich Panel with the activity feed and icons."""
    feed = ""
    for ts, msg, style in activity_feed[-activity_feed_max:]:
        icon = ""
        if "success" in style:
            icon = "✅ "
        elif "error" in style:
            icon = "❌ "
        elif "warning" in style:
            icon = "⚠️ "
        elif "info" in style:
            icon = "ℹ️ "
        feed += f"[{style}][{ts}] {icon}{msg}\n"
    if not feed:
        feed = "[dim]No activity yet."
    return Panel(feed.rstrip(), title="[bold blue]Activity Feed", border_style="bright_magenta", padding=(0,1), width=min(console.width, 80), height=None, box=box.ROUNDED)

def get_layout():
    layout = Layout()
    # Header
    header = Text()
    header.append("\n╔════════════════════════════════════════════╗\n", style="bold cyan")
    header.append("║      ", style="bold cyan")
    header.append("💎 Jacobs Crypto Tools 💎", style="bold magenta")
    header.append("            ║\n", style="bold cyan")
    header.append("╚════════════════════════════════════════════╝\n", style="bold cyan")
    header_panel = Align.center(header)
    # Divider
    divider = Align.center(Text("─" * (min(console.width, 50)), style="dim"))
    # Footer
    footer = Align.center(Text("Tip: Type /help for commands | v1.0", style="dim"))
    # Compose layout
    layout.split_column(
        Layout(header_panel, name="header", size=4),
        Layout(divider, name="divider", size=1),
        Layout(get_status_panel(), name="status", size=8),
        Layout(get_activity_panel(), name="activity"),
        Layout(footer, name="footer", size=1),
    )
    return layout

# --- Footer ---
def print_footer():
    footer = Text()
    footer.append("Tip: Type /help for commands | v1.0", style="dim")
    console.print(Align.center(footer))

def command_input_thread(live):
    while True:
        try:
            # Pause live rendering for input
            cmd = live.console.input("[bold magenta]Enter command (or /help): ")
            command_queue.put(cmd)
        except (KeyboardInterrupt, EOFError):
            break

def handle_command(cmd):
    cmd = cmd.strip().lower()
    if cmd in ('/help', 'help'):
        print_menu()
    elif cmd in ('/status', 'status'):
        console.print(get_status_panel())
    elif cmd in ('/last', 'last'):
        console.print(f"[yellow]Last contract:[/] {status_data['last_contract']} from [green]{status_data['last_channel']}")
    elif cmd in ('/clear', 'clear'):
        activity_feed.clear()
        print_status("Activity feed cleared.", "info")
    elif cmd in ('/start', 'start'):
        print_status("Bot is running and monitoring for contract addresses!", "success")
    elif cmd == '':
        pass
    else:
        print_status(f"Unknown command: {cmd}", "warning")

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

# Persistent storage for processed contract addresses
PROCESSED_CONTRACTS_FILE = 'processed_contracts.txt'
processed_contracts = set()

# Notification chat ID from environment
NOTIFY_CHAT_ID = os.getenv('NOTIFY_CHAT_ID')

def load_processed_contracts():
    """Load processed contract addresses from file into a set."""
    global processed_contracts
    if os.path.exists(PROCESSED_CONTRACTS_FILE):
        with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
            processed_contracts = set(line.strip() for line in f if line.strip())
    else:
        processed_contracts = set()

def save_processed_contract(ca):
    """Append a processed contract address to the file."""
    with open(PROCESSED_CONTRACTS_FILE, 'a') as f:
        f.write(ca + '\n')

async def send_notification(client, message):
    """Send a notification message to the configured chat ID."""
    if NOTIFY_CHAT_ID:
        try:
            await client.send_message(int(NOTIFY_CHAT_ID), message)
        except PeerIdInvalidError:
            print_status(f"Invalid NOTIFY_CHAT_ID: {NOTIFY_CHAT_ID}", "error")
        except Exception as e:
            print_status(f"Failed to send notification: {e}", "error")

def local_notify(title, message, success=True):
    """Show a popup and play a sound on Windows for local notification."""
    if platform.system() == 'Windows':
        # Play different sounds for success and failure
        if success:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)  # Info sound
        else:
            winsound.MessageBeep(winsound.MB_ICONHAND)      # Error sound
        # Show a popup
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)

def desktop_notify(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Jacobs Crypto Tools",
            timeout=5
        )
    except Exception as e:
        print(f"Desktop notification failed: {e}")

async def handle_new_message(event):
    """Handle new messages and forward contract addresses."""
    try:
        chat = await event.get_chat()
        if not hasattr(chat, 'username'):
            return
        channel_username = chat.username
        if not channel_username:
            return
        print_status(f"Received message from channel: @{channel_username}", "info")
        print_status(f"Message content: {event.message.text}", "info")
        target_channels = [channel.lstrip('@') for channel in get_target_channels()]
        if channel_username not in target_channels:
            print_status(f"Channel @{channel_username} not in target channels: {target_channels}", "info")
            return
        message_text = event.message.text
        contract_addresses = re.findall(os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}'), message_text)
        if not contract_addresses:
            print_status("No contract addresses found in message", "info")
            return
        print_status(f"Found contract addresses: {contract_addresses}", "success")
        for ca in contract_addresses:
            if ca in processed_contracts:
                print_status(f"Contract address {ca} already processed. Skipping.", "warning")
                status_data['last_status'] = 'Skipped (duplicate)'
                continue
            try:
                await event.client.send_message(
                    os.getenv('AUTOBUY_BOT_USERNAME'),
                    ca
                )
                print_status(f"Forwarded contract address from @{channel_username}: {ca}", "success")
                processed_contracts.add(ca)
                save_processed_contract(ca)
                status_data['processed_count'] += 1
                status_data['last_contract'] = ca
                status_data['last_channel'] = channel_username
                status_data['last_status'] = 'Success'
                notify_msg = f"✅ Buy triggered for contract: {ca} from channel @{channel_username} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                await send_notification(event.client, notify_msg)
                local_notify("Buy Triggered", f"Buy triggered for contract: {ca} from @{channel_username}", success=True)
                desktop_notify("Buy Triggered", f"Buy triggered for contract: {ca} from @{channel_username}")
            except Exception as e:
                print_status(f"Error forwarding contract address from @{channel_username}: {e}", "error")
                status_data['last_contract'] = ca
                status_data['last_channel'] = channel_username
                status_data['last_status'] = 'Failed'
                notify_msg = f"❌ Failed to buy contract: {ca} from channel @{channel_username}. Error: {str(e)}"
                await send_notification(event.client, notify_msg)
                local_notify("Buy Failed", f"Failed to buy contract: {ca} from @{channel_username}\nError: {str(e)}", success=False)
                desktop_notify("Buy Failed", f"Failed to buy contract: {ca} from @{channel_username}\nError: {str(e)}")
    except Exception as e:
        print_status(f"Error processing message: {e}", "error")

async def telegram_client_task(client):
    await client.start()
    await client.run_until_disconnected()

async def main():
    print_banner()
    print_menu()
    print_status("Starting up...", "info")
    if not check_environment():
        sys.exit(1)
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = get_target_channels()
    autobuy_bot = os.getenv('AUTOBUY_BOT_USERNAME')
    status_data['channels'] = target_channels
    load_processed_contracts()
    client = TelegramClient('monitor_session', api_id, api_hash)
    client.add_event_handler(handle_new_message, events.NewMessage(chats=target_channels))
    print_status("Client is now running!", "success")
    print_status(f"Monitoring channels: {', '.join(target_channels)}", "info")
    print_status(f"Forwarding to: @{autobuy_bot}", "info")
    print_status("Waiting for contract addresses...", "info")
    tg_task = asyncio.create_task(telegram_client_task(client))
    try:
        while True:
            # Show dashboard
            with Live(get_layout(), refresh_per_second=2, screen=True, console=console):
                await asyncio.sleep(0.1)  # Let the dashboard render briefly
            # Prompt for input outside Live context
            cmd = await asyncio.to_thread(console.input, "[bold magenta]Enter command (or /help): ")
            handle_command(cmd)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Client stopped by user. Goodbye!")
    except Exception as e:
        print_status(f"Unexpected error: {e}", "error")
        console.print(f"\n[red]❌ Client encountered an error and needs to stop.")
        console.print(f"[red]Please check the error message above and try again.")
        sys.exit(1)
    finally:
        tg_task.cancel()

if __name__ == '__main__':
    asyncio.run(main()) 