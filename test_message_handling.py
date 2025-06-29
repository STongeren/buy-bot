import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_contract_detection():
    """Test if contract addresses are being detected correctly"""
    print("🔍 Testing contract address detection...")
    
    # Test messages with contract addresses
    test_messages = [
        "Check out this contract: 0x1234567890123456789012345678901234567890",
        "New token: 0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        "Contract: 0x1111111111111111111111111111111111111111",
        "No contract here",
        "Multiple contracts: 0x2222222222222222222222222222222222222222 and 0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
    ]
    
    # Get the pattern from environment or use default
    ca_pattern = os.getenv('CA_PATTERN', r'0x[a-fA-F0-9]{40}')
    print(f"Using pattern: {ca_pattern}")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        contract_addresses = re.findall(ca_pattern, message)
        if contract_addresses:
            print(f"✅ Found contracts: {contract_addresses}")
        else:
            print("❌ No contracts found")
    
    # Test channel filtering
    print(f"\n🔍 Testing channel filtering...")
    target_channels = os.getenv('TARGET_CHANNELS', '').split(',')
    target_channels = [channel.strip().lstrip('@') for channel in target_channels if channel.strip()]
    print(f"Target channels: {target_channels}")
    
    test_channels = ['@thisstest', '@StriderCalls', '@StereoCalls', '@GRODTCALLS', '@TheEntryClub', '@YoungBoyGems', '@SomeOtherChannel']
    
    for channel in test_channels:
        channel_username = channel.lstrip('@')
        if channel_username in target_channels:
            print(f"✅ {channel} is in target list")
        else:
            print(f"❌ {channel} is NOT in target list")

def test_environment():
    """Test environment variables"""
    print("🔍 Testing environment variables...")
    
    required_vars = ['API_ID', 'API_HASH', 'AUTOBUY_BOT_USERNAME', 'TARGET_CHANNELS']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var in ['API_ID', 'API_HASH']:
                print(f"✅ {var}: {'Set' if value else 'Missing'}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Missing")

if __name__ == '__main__':
    test_environment()
    print("\n" + "="*50)
    test_contract_detection() 