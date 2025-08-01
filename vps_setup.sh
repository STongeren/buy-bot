#!/bin/bash
set -e

echo "Setting up VPS environment..."

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3 python3-pip git screen curl wget -y

# Create bot directory
mkdir -p /opt/buy-bot
cd /opt/buy-bot

# Install Python packages
pip3 install --upgrade pip
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
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable buy-bot

# Set proper permissions
chmod 600 /opt/buy-bot/.env
chmod 644 /opt/buy-bot/*.py
chmod 644 /opt/buy-bot/*.txt

echo "VPS setup complete!"
echo ""
echo "Environment validation:"
echo "✅ Python dependencies installed"
echo "✅ Systemd service configured"
echo "✅ Files deployed to /opt/buy-bot"
echo "✅ Permissions set correctly"
echo ""
echo "Next steps:"
echo "1. Start the bot: systemctl start buy-bot"
echo "2. Check status: systemctl status buy-bot"
echo "3. View logs: journalctl -u buy-bot -f"
echo "4. Monitor logs: journalctl -u buy-bot -f --since '5 minutes ago'"
echo ""
echo "First time setup (if needed):"
echo "1. Stop service: systemctl stop buy-bot"
echo "2. Run manually: cd /opt/buy-bot && python3 monitor_vps.py"
echo "3. Authenticate with Telegram when prompted"
echo "4. Restart service: systemctl start buy-bot"
