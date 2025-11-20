#!/usr/bin/env python3
"""
Instrument Mapper Test Script
Run this on PythonAnywhere to diagnose instrument fetching issues

Usage:
  python3 scripts/test_instrument_mapper.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/home/mhdSharuk/upstox_swing')

import requests
from auth.token_manager import TokenManager
from storage.supabase_storage import SupabaseStorage
from config.env_loader import SUPABASE_URL, SUPABASE_KEY
from config.settings import API_CONFIG, INSTRUMENT_FILTERS

print("=" * 60)
print("INSTRUMENT MAPPER DIAGNOSTIC TEST")
print("=" * 60)

# Test 1: Load token
print("\n1. Loading Upstox token...")
try:
    supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
    supabase_storage.authenticate()
    
    token_manager = TokenManager(
        token_file="upstox_token.json",
        use_supabase=True,
        supabase_storage=supabase_storage
    )
    
    if not token_manager.load_token():
        print("   ✗ Failed to load token")
        sys.exit(1)
    
    if not token_manager.validate_token():
        print("   ✗ Token is invalid")
        sys.exit(1)
    
    access_token = token_manager.get_token()
    print(f"   ✓ Token loaded and validated")
    print(f"   User: {token_manager.user_info.get('user_name')}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Check network access to Upstox instruments URL
print("\n2. Testing network access to Upstox instruments URL...")
url = API_CONFIG['instruments_url']
print(f"   URL: {url}")

try:
    print("   Making HEAD request...")
    resp = requests.head(url, timeout=10)
    print(f"   ✓ Status: {resp.status_code}")
    print(f"   Headers: {dict(resp.headers)}")
    
    if resp.status_code != 200:
        print(f"   ✗ Unexpected status code: {resp.status_code}")
        print("   This URL might be blocked on PythonAnywhere")
        print("   Trying GET request...")
        resp = requests.get(url, stream=True, timeout=10)
        print(f"   GET Status: {resp.status_code}")
    
except requests.exceptions.Timeout:
    print("   ✗ Request timed out")
    print("   The URL might be blocked or very slow")
except requests.exceptions.ConnectionError as e:
    print(f"   ✗ Connection error: {e}")
    print("   The URL is likely blocked on PythonAnywhere")
    print("   Check: https://www.pythonanywhere.com/whitelist/")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Try fetching a small sample
print("\n3. Testing instrument data download (first 100KB)...")
try:
    import gzip
    import io
    
    print("   Downloading...")
    resp = requests.get(url, stream=True, timeout=30)
    
    # Read first 100KB
    chunk = resp.raw.read(100 * 1024)
    print(f"   ✓ Downloaded {len(chunk)} bytes")
    
    print("   Decompressing...")
    decompressed = gzip.decompress(chunk)
    print(f"   ✓ Decompressed to {len(decompressed)} bytes")
    
    print("   Sample data (first 500 chars):")
    print(decompressed[:500].decode('utf-8', errors='ignore'))
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Try using the actual InstrumentMapper
print("\n4. Testing InstrumentMapper class...")
try:
    from data_fetcher.instrument_mapper import InstrumentMapper
    
    print("   Creating mapper instance...")
    mapper = InstrumentMapper(access_token)
    
    print("   Fetching instruments (this may take 1-2 minutes)...")
    success = mapper.fetch_instruments(None)
    
    if success:
        print(f"   ✓ Fetch successful")
        print(f"   Instruments found: {len(mapper.instruments_df)}")
        
        print("   Creating mapping...")
        mapping = mapper.create_mapping()
        
        if mapping:
            print(f"   ✓ Mapping created with {len(mapping)} symbols")
            print("   Sample symbols:")
            for i, symbol in enumerate(list(mapping.keys())[:5]):
                print(f"     - {symbol}")
        else:
            print("   ✗ Mapping creation failed")
    else:
        print("   ✗ Fetch failed")
        
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check allowed domains on PythonAnywhere
print("\n5. Checking if Upstox domains are whitelisted...")
print("   Note: PythonAnywhere requires domains to be whitelisted for free accounts")
print("   Required domain: assets.upstox.com")
print("   Check your whitelist at: https://www.pythonanywhere.com/whitelist/")

print("\n" + "=" * 60)
print("DIAGNOSTIC TEST COMPLETE")
print("=" * 60)

print("\nNEXT STEPS:")
print("1. If 'Connection error' in Test 2:")
print("   → Add 'assets.upstox.com' to PythonAnywhere whitelist")
print("   → URL: https://www.pythonanywhere.com/whitelist/") 
print("")
print("2. If tests pass but flask_app fails:")
print("   → Check flask_app.py logs for detailed error")
print("   → Ensure all imports work correctly")
print("")
print("3. If whitelist issue:")
print("   → Free accounts have limited whitelist")
print("   → May need to upgrade to paid account")
print("   → Or use alternative data source")