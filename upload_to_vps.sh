#!/bin/bash

# VPS details
VPS_IP="67.217.228.153"
VPS_USER="root"

echo "Uploading files to VPS..."

# Upload files
scp monitor_vps.py $VPS_USER@$VPS_IP:/tmp/
scp requirements.txt $VPS_USER@$VPS_IP:/tmp/
scp .env $VPS_USER@$VPS_IP:/tmp/

echo "Files uploaded. Now setting up on VPS..."

# Run setup commands on VPS
ssh $VPS_USER@$VPS_IP << 'EOF'
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3 python3-pip git -y

# Create bot directory
mkdir -p /opt/buy-bot
cd /opt/buy-bot

# Copy files
cp /tmp/monitor_vps.py .
cp /tmp/requirements.txt .
cp /tmp/.env .

# Install Python packages
pip3 install -r requirements.txt

# Set permissions
chmod 600 .env
chown -R root:root .

echo "Setup complete! Bot files are in /opt/buy-bot"
echo "To run the bot: cd /opt/buy-bot && python3 monitor_vps.py"
EOF

echo "VPS setup complete!"
echo "SSH into your VPS and run: cd /opt/buy-bot && python3 monitor_vps.py" 