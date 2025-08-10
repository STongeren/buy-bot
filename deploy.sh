#!/bin/bash
# Simple VPS deployment - replaces 10+ complex scripts with 3 commands

VPS="root@67.217.228.153"

echo "🚀 Deploying Telegram Bot to VPS..."

# 1. Upload essential files
echo "📤 Uploading files..."
ssh $VPS "mkdir -p /opt/telegram-bot"
scp monitor_bot.py requirements.txt .env $VPS:/opt/telegram-bot/

# 2. Setup environment
echo "⚙️ Setting up environment..."
ssh $VPS "
cd /opt/telegram-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
"

# 3. Create service and start
echo "🚀 Creating service..."
ssh $VPS "
cat > /etc/systemd/system/telegram-bot.service << 'EOF'
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/telegram-bot
ExecStart=/opt/telegram-bot/venv/bin/python monitor_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable telegram-bot
systemctl start telegram-bot
"

echo "✅ Done! Check status with: ssh $VPS 'systemctl status telegram-bot'"
echo "📱 Your bot @JCBSERVICESXBOT is now running 24/7!"