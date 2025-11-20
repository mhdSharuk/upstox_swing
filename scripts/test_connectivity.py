"""
Diagnostic script to test API connectivity on PythonAnywhere
Run this first to identify the exact issue
"""

import sys
import asyncio
import aiohttp
import ssl
import certifi

# Test 1: Basic connectivity test with requests
def test_with_requests():
    """Test if requests library works (should work on PythonAnywhere)"""
    print("\n" + "="*60)
    print("TEST 1: Testing with requests library")
    print("="*60)
    try:
        import requests
        response = requests.get("https://api.upstox.com/v2/market/holidays/NSE", timeout=10)
        print(f"✓ Status Code: {response.status_code}")
        print(f"✓ Response: {response.text[:200]}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


# Test 2: Test aiohttp with default SSL
async def test_aiohttp_default():
    """Test aiohttp with default configuration"""
    print("\n" + "="*60)
    print("TEST 2: Testing aiohttp with default SSL")
    print("="*60)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.upstox.com/v2/market/holidays/NSE", timeout=10) as response:
                print(f"✓ Status Code: {response.status}")
                text = await response.text()
                print(f"✓ Response: {text[:200]}")
                return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 3: Test aiohttp with certifi SSL
async def test_aiohttp_certifi():
    """Test aiohttp with certifi SSL context"""
    print("\n" + "="*60)
    print("TEST 3: Testing aiohttp with certifi SSL")
    print("="*60)
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://api.upstox.com/v2/market/holidays/NSE", timeout=10) as response:
                print(f"✓ Status Code: {response.status}")
                text = await response.text()
                print(f"✓ Response: {text[:200]}")
                return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 4: Test aiohttp with SSL disabled (not recommended but diagnostic)
async def test_aiohttp_no_ssl():
    """Test aiohttp with SSL verification disabled"""
    print("\n" + "="*60)
    print("TEST 4: Testing aiohttp with SSL disabled")
    print("="*60)
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get("https://api.upstox.com/v2/market/holidays/NSE", timeout=10) as response:
                print(f"✓ Status Code: {response.status}")
                text = await response.text()
                print(f"✓ Response: {text[:200]}")
                return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test 5: Test aiohttp with trust_env
async def test_aiohttp_trust_env():
    """Test aiohttp with trust_env=True"""
    print("\n" + "="*60)
    print("TEST 5: Testing aiohttp with trust_env=True")
    print("="*60)
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
            async with session.get("https://api.upstox.com/v2/market/holidays/NSE", timeout=10) as response:
                print(f"✓ Status Code: {response.status}")
                text = await response.text()
                print(f"✓ Response: {text[:200]}")
                return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests"""
    print("\n" + "="*70)
    print("PYTHONANYWHERE API CONNECTIVITY DIAGNOSTIC")
    print("="*70)
    print("\nThis will test different methods to connect to Upstox API")
    print("We're testing: https://api.upstox.com/v2/market/holidays/NSE")
    
    # Check Python version
    print(f"\nPython Version: {sys.version}")
    
    # Check if certifi is installed
    try:
        import certifi
        print(f"Certifi Version: {certifi.__version__}")
        print(f"Certifi Path: {certifi.where()}")
    except ImportError:
        print("⚠️  WARNING: certifi not installed! Run: pip install --user certifi")
    
    # Check aiohttp version
    try:
        import aiohttp
        print(f"aiohttp Version: {aiohttp.__version__}")
    except ImportError:
        print("⚠️  ERROR: aiohttp not installed!")
        return
    
    results = {}
    
    # Test 1: requests library
    results['requests'] = test_with_requests()
    
    # Test 2-5: aiohttp variations
    results['aiohttp_default'] = asyncio.run(test_aiohttp_default())
    results['aiohttp_certifi'] = asyncio.run(test_aiohttp_certifi())
    results['aiohttp_no_ssl'] = asyncio.run(test_aiohttp_no_ssl())
    results['aiohttp_trust_env'] = asyncio.run(test_aiohttp_trust_env())
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:25} : {status}")
    
    print("\n" + "="*70)
    if results['requests']:
        print("✓ Your PythonAnywhere account CAN access Upstox API")
        if not any([results['aiohttp_default'], results['aiohttp_certifi'], results['aiohttp_trust_env']]):
            print("⚠️  Issue: aiohttp has SSL/connectivity problems")
            print("\nPossible solutions:")
            print("1. Upgrade PythonAnywhere account (free accounts have limited external access)")
            print("2. Contact PythonAnywhere support about aiohttp SSL issues")
            if results['aiohttp_no_ssl']:
                print("3. Consider using SSL=False temporarily (not recommended for production)")
    else:
        print("✗ Your PythonAnywhere account CANNOT access Upstox API")
        print("\nRequired actions:")
        print("1. Verify api.upstox.com is whitelisted (requires paid account)")
        print("2. Check account settings at: https://www.pythonanywhere.com/user/mhdsharuk/account/")
        print("3. Upgrade to a paid plan if on free tier")
    print("="*70)


if __name__ == "__main__":
    main()