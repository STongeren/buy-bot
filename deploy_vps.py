#!/usr/bin/env python3
"""
VPS Deployment Script for Telegram Contract Monitor Bot
"""

import os
import subprocess
import sys
import getpass
from pathlib import Path

def run_command(command, check=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    return result.stdout

def deploy_to_vps():
    """Deploy the bot to VPS"""
    print("Starting VPS Deployment...")
    
    # VPS details
    vps_ip = "67.217.228.153"
    
    # Get SSH credentials
    print(f"\nVPS Details:")
    print(f"IP: {vps_ip}")
    username = input("Enter VPS username (default: root): ").strip() or "root"
    password = getpass.getpass("Enter VPS password: ")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print(".env file not found! Please create it first with your API credentials.")
        return False
    
    print("\nPreparing files for deployment...")
    
    # Create deployment package
    files_to_deploy = [
        'monitor_vps.py',
        'requirements.txt',
        '.env',
        'README.md'
    ]
    
    # Check if all files exist
    missing_files = []
    for file in files_to_deploy:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    
    print("All required files found")
    
    # Create deployment script
    deploy_script = """#!/bin/bash
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
"""
    
    # Save deployment script
    with open('vps_setup.sh', 'w', encoding='utf-8') as f:
        f.write(deploy_script)
    
    print("Uploading files to VPS...")
    
    # Upload files using scp
    for file in files_to_deploy + ['vps_setup.sh']:
        upload_cmd = f'scp {file} {username}@{vps_ip}:/tmp/'
        if not run_command(upload_cmd):
            print(f"Failed to upload {file}")
            return False
    
    print("Files uploaded successfully")
    
    # Execute setup script on VPS
    print("\nRunning setup on VPS...")
    
    setup_commands = [
        f"ssh {username}@{vps_ip} 'chmod +x /tmp/vps_setup.sh'",
        f"ssh {username}@{vps_ip} 'sudo /tmp/vps_setup.sh'",
        f"ssh {username}@{vps_ip} 'sudo cp /tmp/*.py /tmp/*.txt /tmp/.env /opt/buy-bot/'",
        f"ssh {username}@{vps_ip} 'sudo chown -R root:root /opt/buy-bot'",
        f"ssh {username}@{vps_ip} 'sudo chmod 600 /opt/buy-bot/.env'"
    ]
    
    for cmd in setup_commands:
        if not run_command(cmd):
            print(f"Setup command failed: {cmd}")
            return False
    
    print("VPS setup completed successfully!")
    
    # Clean up local files
    os.remove('vps_setup.sh')
    
    print("\nDeployment Complete!")
    print("\nNext Steps:")
    print("1. SSH into your VPS: ssh root@67.217.228.153")
    print("2. Start the bot: systemctl start buy-bot")
    print("3. Check status: systemctl status buy-bot")
    print("4. View logs: journalctl -u buy-bot -f")
    print("\nFirst time setup:")
    print("1. Stop service: systemctl stop buy-bot")
    print("2. Run manually: cd /opt/buy-bot && python3 monitor_vps.py")
    print("3. Authenticate with Telegram")
    print("4. Restart service: systemctl start buy-bot")
    
    return True

if __name__ == "__main__":
    try:
        success = deploy_to_vps()
        if success:
            print("\nDeployment successful!")
        else:
            print("\nDeployment failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nDeployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1) 