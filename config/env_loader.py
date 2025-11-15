"""
Environment Variable Loader
Loads credentials from .env file or environment variables
Falls back to credentials.py if env vars not available
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Load .env file if it exists
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    load_dotenv(env_file)
    # print(f"✓ Loaded environment variables from {env_file}")
else:
    print(f"⚠ No .env file found at {env_file}, using system environment variables")

# ==================== UPSTOX API CREDENTIALS ====================
UPSTOX_API_KEY = os.getenv('UPSTOX_API_KEY')
UPSTOX_API_SECRET = os.getenv('UPSTOX_API_SECRET')
UPSTOX_CLIENT_ID = os.getenv('UPSTOX_CLIENT_ID')
UPSTOX_REDIRECT_URI = os.getenv('UPSTOX_REDIRECT_URI', 'http://localhost:8000')
UPSTOX_TOTP_SECRET = os.getenv('UPSTOX_TOTP_SECRET')

# ==================== FLASK APP CONFIGURATION ====================
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://mhdsharuk.pythonanywhere.com/upstox-webhook')
PYTHONANYWHERE_USERNAME = os.getenv('PYTHONANYWHERE_USERNAME', 'mhdSharuk')
FLASK_BASE_URL = os.getenv('FLASK_BASE_URL', 'https://mhdsharuk.pythonanywhere.com')

# ==================== GOOGLE SHEETS CREDENTIALS ====================
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', 'service_account.json')

# ==================== VALIDATION ====================
def validate_credentials():
    """
    Validate that all required credentials are loaded
    Returns: (is_valid, missing_vars)
    """
    required_vars = {
        'UPSTOX_API_KEY': UPSTOX_API_KEY,
        'UPSTOX_API_SECRET': UPSTOX_API_SECRET,
        'UPSTOX_CLIENT_ID': UPSTOX_CLIENT_ID,
        'UPSTOX_TOTP_SECRET': UPSTOX_TOTP_SECRET,
        'FLASK_SECRET_KEY': FLASK_SECRET_KEY,
        'GOOGLE_SHEET_ID': GOOGLE_SHEET_ID,
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    
    if missing:
        return False, missing
    
    return True, []


# ==================== FALLBACK TO credentials.py ====================
# If environment variables are not set, try loading from credentials.py
is_valid, missing = validate_credentials()

if not is_valid:
    print(f"⚠ Missing environment variables: {missing}")
    print("⚠ Attempting to load from config/credentials.py as fallback...")
    
    try:
        from .credentials import (
            UPSTOX_API_KEY as cred_api_key,
            UPSTOX_API_SECRET as cred_api_secret,
            UPSTOX_CLIENT_ID as cred_client_id,
            UPSTOX_REDIRECT_URI as cred_redirect_uri,
            UPSTOX_TOTP_SECRET as cred_totp_secret,
            FLASK_SECRET_KEY as cred_flask_secret,
            GOOGLE_SHEET_ID as cred_sheet_id,
            SERVICE_ACCOUNT_FILE as cred_service_account,
            WEBHOOK_URL as cred_webhook_url,
        )
        
        # Use credentials.py values if env vars are not set
        UPSTOX_API_KEY = UPSTOX_API_KEY or cred_api_key
        UPSTOX_API_SECRET = UPSTOX_API_SECRET or cred_api_secret
        UPSTOX_CLIENT_ID = UPSTOX_CLIENT_ID or cred_client_id
        UPSTOX_REDIRECT_URI = UPSTOX_REDIRECT_URI or cred_redirect_uri
        UPSTOX_TOTP_SECRET = UPSTOX_TOTP_SECRET or cred_totp_secret
        FLASK_SECRET_KEY = FLASK_SECRET_KEY or cred_flask_secret
        GOOGLE_SHEET_ID = GOOGLE_SHEET_ID or cred_sheet_id
        SERVICE_ACCOUNT_FILE = SERVICE_ACCOUNT_FILE or cred_service_account
        WEBHOOK_URL = WEBHOOK_URL or cred_webhook_url
        
        print("✓ Loaded credentials from config/credentials.py (fallback)")
        
    except ImportError:
        print("✗ ERROR: No credentials.py file found and environment variables not set!")
        print("✗ Please either:")
        print("  1. Create .env file with required variables")
        print("  2. Set environment variables in your system")
        print("  3. Create config/credentials.py")
else:
    pass
    # print("✓ All required credentials loaded from environment variables")


# ==================== EXPORT ALL ====================
__all__ = [
    'UPSTOX_API_KEY',
    'UPSTOX_API_SECRET',
    'UPSTOX_CLIENT_ID',
    'UPSTOX_REDIRECT_URI',
    'UPSTOX_TOTP_SECRET',
    'FLASK_SECRET_KEY',
    'WEBHOOK_URL',
    'PYTHONANYWHERE_USERNAME',
    'FLASK_BASE_URL',
    'GOOGLE_SHEET_ID',
    'SERVICE_ACCOUNT_FILE',
    'validate_credentials',
]