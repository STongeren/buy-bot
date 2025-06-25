import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
MONITOR_BOT_TOKEN = os.getenv('MONITOR_BOT_TOKEN')
AUTOBUY_BOT_USERNAME = os.getenv('AUTOBUY_BOT_USERNAME')
TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')
CA_PATTERN = os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}')
PROCESSED_CONTRACTS_FILE = 'processed_contracts.txt'
processed_contracts = set()

def load_processed_contracts():
    global processed_contracts
    if os.path.exists(PROCESSED_CONTRACTS_FILE):
        with open(PROCESSED_CONTRACTS_FILE, 'r') as f:
            processed_contracts = set(line.strip() for line in f if line.strip())
    else:
        processed_contracts = set()

def save_processed_contract(ca):
    with open(PROCESSED_CONTRACTS_FILE, 'a') as f:
        f.write(ca + '\n')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Bot is running and monitoring for contract addresses!')

async def forward_contract_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process messages and forward contract addresses to the autobuy bot, skipping duplicates."""
    if not update.channel_post:
        return

    # Check if the message is from the target channel
    if update.channel_post.chat.username != TARGET_CHANNEL.lstrip('@'):
        return

    # Extract contract addresses from the message
    message_text = update.channel_post.text
    contract_addresses = re.findall(CA_PATTERN, message_text)

    if not contract_addresses:
        return

    for ca in contract_addresses:
        if ca in processed_contracts:
            logger.info(f"Contract address {ca} already processed. Skipping.")
            continue
        try:
            await context.bot.send_message(
                chat_id=f"@{AUTOBUY_BOT_USERNAME}",
                text=ca
            )
            logger.info(f"Forwarded contract address: {ca}")
            processed_contracts.add(ca)
            save_processed_contract(ca)
        except Exception as e:
            logger.error(f"Error forwarding contract address: {e}")

def main():
    """Start the bot."""
    load_processed_contracts()
    application = Application.builder().token(MONITOR_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_contract_address))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 