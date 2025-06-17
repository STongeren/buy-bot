# Telegram Contract Address Monitor Bot

This bot monitors a specified Telegram channel for messages containing contract addresses and automatically forwards them to an autobuy bot.

## Features

- Monitors a specific Telegram channel for messages
- Automatically extracts contract addresses from messages
- Forwards contract addresses to an autobuy bot
- Configurable contract address pattern matching
- Logging of all activities

## Setup

1. Create a new Telegram bot using [@BotFather](https://t.me/botfather) and get the bot token
2. Clone this repository
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file based on `.env.example` and fill in your configuration:
   - `MONITOR_BOT_TOKEN`: Your monitor bot's token from BotFather
   - `AUTOBUY_BOT_USERNAME`: The username of your autobuy bot (without @)
   - `TARGET_CHANNEL`: The channel to monitor (with @ symbol)
   - `CA_PATTERN`: (Optional) Custom regex pattern for contract addresses

## Usage

1. Add your monitor bot to the target channel as an admin
2. Start the bot:
   ```bash
   python monitor_bot.py
   ```
3. The bot will automatically:
   - Monitor the specified channel
   - Extract contract addresses from messages
   - Forward them to the autobuy bot

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- Ensure your bot has the necessary permissions in the target channel
- Regularly check the logs for any issues

## Troubleshooting

If the bot isn't working as expected:
1. Check that all environment variables are set correctly
2. Verify the bot has admin access to the target channel
3. Check the logs for any error messages
4. Ensure the autobuy bot username is correct and the bot is active 