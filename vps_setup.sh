#!/bin/bash
set -e

echo "Setting up VPS environment..."

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3 python3-pip git screen -y

# Create bot directory
mkdir -p /opt/buy-bot
cd /opt/buy-bot

# Install Python packages
pip3 install -r requirements.txt

# Set up systemd service
cat > /etc/systemd/system/buy-bot.service << 'EOF'
[Unit]
Description=Telegram Contract Monitor Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/buy-bot
ExecStart=/usr/bin/python3 monitor_vps.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable buy-bot

echo "VPS setup complete!"
echo "Next steps:"
echo "1. Run: systemctl start buy-bot"
echo "2. Check status: systemctl status buy-bot"
echo "3. View logs: journalctl -u buy-bot -f"
