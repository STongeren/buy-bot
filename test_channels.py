import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError

# Load environment variables
load_dotenv()

async def test_channels():
    """Test channel connectivity and permissions"""
    print("🔍 Testing channel connectivity...")
    
    # Check environment variables
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    target_channels = os.getenv('TARGET_CHANNELS', '').split(',')
    target_channels = [channel.strip() for channel in target_channels if channel.strip()]
    
    print(f"API_ID: {'✅ Set' if api_id else '❌ Missing'}")
    print(f"API_HASH: {'✅ Set' if api_hash else '❌ Missing'}")
    print(f"Target channels: {target_channels}")
    
    if not api_id or not api_hash:
        print("❌ Missing API credentials. Please check your .env file")
        return
    
    if not target_channels:
        print("❌ No target channels specified in TARGET_CHANNELS")
        return
    
    # Create client
    client = TelegramClient('test_session', api_id, api_hash)
    
    try:
        await client.start()
        print("✅ Successfully connected to Telegram")
        
        # Test each channel
        for channel in target_channels:
            print(f"\n🔍 Testing channel: {channel}")
            
            try:
                # Try to get channel entity
                if channel.startswith('@'):
                    entity = await client.get_entity(channel)
                else:
                    entity = await client.get_entity(f"@{channel}")
                
                print(f"✅ Channel found: {entity.title}")
                
                # Try to get recent messages
                try:
                    messages = await client.get_messages(entity, limit=1)
                    if messages:
                        print(f"✅ Can read messages from {channel}")
                    else:
                        print(f"⚠️ No recent messages found in {channel}")
                except ChannelPrivateError:
                    print(f"❌ Cannot read messages from {channel} - channel is private or bot not a member")
                except Exception as e:
                    print(f"❌ Error reading messages from {channel}: {e}")
                    
            except UsernameNotOccupiedError:
                print(f"❌ Channel {channel} does not exist")
            except ChannelPrivateError:
                print(f"❌ Channel {channel} is private - bot needs to be added as member")
            except Exception as e:
                print(f"❌ Error accessing {channel}: {e}")
                
    except Exception as e:
        print(f"❌ Failed to connect to Telegram: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(test_channels()) 