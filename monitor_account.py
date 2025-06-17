import os
import re
import sys
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set."""
    required_vars = ['BOT_TOKEN', 'AUTOBUY_BOT_USERNAME', 'TARGET_CHANNEL']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"- {var}")
        logger.error("\nPlease check your .env file and make sure all variables are set correctly.")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Bot is running and monitoring for contract addresses!')

async def forward_contract_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process messages and forward contract addresses to the autobuy bot."""
    if not update.channel_post:
        return

    # Check if the message is from the target channel
    if update.channel_post.chat.username != os.getenv('TARGET_CHANNEL').lstrip('@'):
        return

    # Extract contract addresses from the message
    message_text = update.channel_post.text
    contract_addresses = re.findall(os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}'), message_text)

    if not contract_addresses:
        return

    # Forward each contract address to the autobuy bot
    for ca in contract_addresses:
        try:
            # Send the contract address to the autobuy bot
            await context.bot.send_message(
                chat_id=f"@{os.getenv('AUTOBUY_BOT_USERNAME')}",
                text=ca
            )
            logger.info(f"✅ Forwarded contract address: {ca}")
        except Exception as e:
            logger.error(f"❌ Error forwarding contract address: {e}")

def main():
    """Main function to run the bot."""
    print("\n=== Telegram Contract Address Monitor ===")
    print("Starting up...\n")
    
    # Check environment variables
    if not check_environment():
        sys.exit(1)
    
    # Get configuration
    bot_token = os.getenv('BOT_TOKEN')
    target_channel = os.getenv('TARGET_CHANNEL')
    autobuy_bot = os.getenv('AUTOBUY_BOT_USERNAME')
    
    # Create the Application
    application = Application.builder().token(bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, forward_contract_address))
    
    print(f"\n✅ Bot is now running!")
    print(f"📢 Monitoring channel: {target_channel}")
    print(f"🤖 Forwarding to: @{autobuy_bot}")
    print("\nPress Ctrl+C to stop the bot\n")
    
    try:
        # Start the Bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n\nBot stopped by user. Goodbye!")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 