import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import Channel

# Load environment variables
load_dotenv()

async def test_live_monitoring():
    """Test if the bot can receive live messages"""
    print("🔍 Testing live message monitoring...")
    
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = os.getenv('TARGET_CHANNELS', '').split(',')
    target_channels = [channel.strip() for channel in target_channels if channel.strip()]
    
    if not api_id or not api_hash:
        print("❌ Missing API credentials")
        return
    
    if not target_channels:
        print("❌ No target channels specified")
        return
    
    print(f"Monitoring channels: {target_channels}")
    
    # Create client
    client = TelegramClient('test_live_session', api_id, api_hash)
    
    @client.on(events.NewMessage(chats=target_channels))
    async def handle_message(event):
        print(f"📨 Received message from {event.chat.username}: {event.message.text[:100]}...")
    
    try:
        await client.start()
        print("✅ Bot is running and listening for messages...")
        print("📝 Send a message to any of the monitored channels to test")
        print("⏹️ Press Ctrl+C to stop")
        
        await client.run_until_disconnected()
        
    except KeyboardInterrupt:
        print("\n👋 Stopping bot...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_live_monitoring()) 