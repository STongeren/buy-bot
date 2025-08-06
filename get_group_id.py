#!/usr/bin/env python3
"""
Script to get group ID for private Telegram groups
"""

import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables
load_dotenv()

async def get_group_info():
    """Get information about private groups"""
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if not api_id or not api_hash:
        print("❌ API_ID or API_HASH not found in .env file")
        return
    
    client = TelegramClient('test_session', api_id, api_hash)
    
    try:
        await client.start()
        print("✅ Connected to Telegram")
        
        # Test private group access
        private_groups = [
            "https://t.me/+6pDxqqnpfqVkMGM8",  # Super Secret Cabal Early CA
            "https://t.me/+hcVwqaZZmu82MWI8"   # test1
        ]
        
        for group in private_groups:
            print(f"\n🔍 Testing group: {group}")
            try:
                # Try to get entity using invite link
                entity = await client.get_entity(group)
                print(f"✅ Success! Group ID: {entity.id}")
                print(f"   Title: {entity.title}")
                print(f"   Username: {getattr(entity, 'username', 'None')}")
                print(f"   Use this in .env: -100{entity.id}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                print("   Try using the invite link format: https://t.me/+hcVwqaZZmu82MWI8")
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(get_group_info()) 