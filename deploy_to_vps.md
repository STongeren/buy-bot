# VPS Deployment Instructions

## Prerequisites
- SSH access to your VPS (67.217.228.153)
- Python 3.8+ installed on VPS
- Git installed on VPS

## Step 1: Connect to VPS
```bash
ssh root@67.217.228.153
```

## Step 2: Install Dependencies
```bash
# Update system
apt update && apt upgrade -y

# Install Python and pip
apt install python3 python3-pip git -y

# Install screen for background running
apt install screen -y
```

## Step 3: Clone Repository
```bash
# Create directory
mkdir -p /opt/buy-bot
cd /opt/buy-bot

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/buy-bot.git .
```

## Step 4: Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

## Step 5: Create Environment File
```bash
nano .env
```

Add your environment variables:
```
API_ID=your_api_id
API_HASH=your_api_hash
AUTOBUY_BOT_USERNAME=based_eth_bot
TARGET_CHANNELS=@thisstest,@StriderCalls,@StereoCalls,@GRODTCALLS,@TheEntryClub,@YoungBoyGems
CA_PATTERN=0x[a-fA-F0-9]{40}
NOTIFY_CHAT_ID=your_chat_id_for_notifications
```

## Step 6: Create Systemd Service
```bash
nano /etc/systemd/system/buy-bot.service
```

Add this content:
```ini
[Unit]
Description=Telegram Contract Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/buy-bot
ExecStart=/usr/bin/python3 monitor_account.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
```

## Step 7: Enable and Start Service
```bash
# Reload systemd
systemctl daemon-reload

# Enable service to start on boot
systemctl enable buy-bot

# Start the service
systemctl start buy-bot

# Check status
systemctl status buy-bot
```

## Step 8: Monitor Logs
```bash
# View real-time logs
journalctl -u buy-bot -f

# View recent logs
journalctl -u buy-bot --since "1 hour ago"
```

## Step 9: First Run Setup
On first run, you'll need to authenticate:
```bash
# Stop the service temporarily
systemctl stop buy-bot

# Run manually to authenticate
cd /opt/buy-bot
python3 monitor_account.py

# After authentication, restart the service
systemctl start buy-bot
```

## Useful Commands
```bash
# Stop bot
systemctl stop buy-bot

# Start bot
systemctl start buy-bot

# Restart bot
systemctl restart buy-bot

# Check status
systemctl status buy-bot

# View logs
journalctl -u buy-bot -f
```

## Security Notes
- Keep your `.env` file secure
- Consider running as a non-root user
- Set up firewall rules if needed
- Regular backups of the session file 