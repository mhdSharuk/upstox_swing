"""
Verification script to check if OAuth2 files are correctly set up
Run this BEFORE running main.py
"""

import os
import json

print("=" * 60)
print("OAUTH2 SETUP VERIFICATION")
print("=" * 60)

errors = []
warnings = []
success = []

# Check 1: OAuth credentials file
print("\n1. Checking OAuth2 credentials file...")
oauth_creds_path = "credentials/oauth_credentials.json"
if os.path.exists(oauth_creds_path):
    try:
        with open(oauth_creds_path, 'r') as f:
            data = json.load(f)
            if 'installed' in data or 'web' in data:
                success.append("✓ OAuth credentials file exists and is valid")
            else:
                errors.append("✗ OAuth credentials file has invalid format")
    except:
        errors.append("✗ OAuth credentials file exists but is not valid JSON")
else:
    errors.append("✗ OAuth credentials file NOT FOUND at: credentials/oauth_credentials.json")

# Check 2: settings.py has OAuth config
print("\n2. Checking config/settings.py...")
try:
    from config.settings import DRIVE_CONFIG
    if 'oauth_credentials_file' in DRIVE_CONFIG:
        success.append("✓ settings.py has oauth_credentials_file configured")
    else:
        errors.append("✗ settings.py missing oauth_credentials_file in DRIVE_CONFIG")
    
    if 'oauth_token_file' in DRIVE_CONFIG:
        success.append("✓ settings.py has oauth_token_file configured")
    else:
        errors.append("✗ settings.py missing oauth_token_file in DRIVE_CONFIG")
except Exception as e:
    errors.append(f"✗ Cannot import settings.py: {e}")

# Check 3: gdrive_handler.py uses OAuth2
print("\n3. Checking storage/gdrive_handler.py...")
try:
    with open('storage/gdrive_handler.py', 'r') as f:
        content = f.read()
        if 'def __init__(self):' in content and 'OAuth2' in content:
            success.append("✓ gdrive_handler.py uses OAuth2 (no service_account_file parameter)")
        elif 'def __init__(self, service_account_file:' in content:
            errors.append("✗ gdrive_handler.py still uses OLD SERVICE ACCOUNT code!")
            errors.append("   You need to replace it with the NEW OAuth2 version!")
        else:
            warnings.append("⚠ Cannot verify gdrive_handler.py __init__ signature")
except FileNotFoundError:
    errors.append("✗ storage/gdrive_handler.py NOT FOUND")
except Exception as e:
    errors.append(f"✗ Error checking gdrive_handler.py: {e}")

# Check 4: main.py calls GoogleDriveHandler correctly
print("\n4. Checking main.py...")
try:
    with open('main.py', 'r') as f:
        content = f.read()
        if 'self.drive_handler = GoogleDriveHandler()' in content:
            success.append("✓ main.py calls GoogleDriveHandler() correctly (no parameters)")
        elif 'GoogleDriveHandler(SERVICE_ACCOUNT_FILE)' in content:
            errors.append("✗ main.py still uses OLD code - calls GoogleDriveHandler with service_account_file!")
        else:
            warnings.append("⚠ Cannot find GoogleDriveHandler initialization in main.py")
except FileNotFoundError:
    errors.append("✗ main.py NOT FOUND")
except Exception as e:
    errors.append(f"✗ Error checking main.py: {e}")

# Print results
print("\n" + "=" * 60)
print("VERIFICATION RESULTS")
print("=" * 60)

if success:
    print("\n✓ SUCCESS:")
    for msg in success:
        print(f"  {msg}")

if warnings:
    print("\n⚠ WARNINGS:")
    for msg in warnings:
        print(f"  {msg}")

if errors:
    print("\n✗ ERRORS:")
    for msg in errors:
        print(f"  {msg}")
    print("\n" + "=" * 60)
    print("FIX ERRORS BEFORE RUNNING main.py!")
    print("=" * 60)
    exit(1)
else:
    print("\n" + "=" * 60)
    print("✓ ALL CHECKS PASSED - READY TO RUN main.py")
    print("=" * 60)
    exit(0)