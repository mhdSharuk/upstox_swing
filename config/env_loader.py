"""
Environment Variable Loader
Loads credentials from .env file or environment variables
UPDATED: Supabase configuration (Google Sheets/Drive removed)
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

# ==================== SUPABASE CREDENTIALS ====================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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
        'SUPABASE_URL': SUPABASE_URL,
        'SUPABASE_KEY': SUPABASE_KEY,
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    
    if missing:
        return False, missing
    
    return True, []


# ==================== FALLBACK TO credentials.py ====================
is_valid, missing = validate_credentials()

if not is_valid:
    print(f"⚠ Missing environment variables: {missing}")
    print("⚠ Attempting to load from config/credentials.py as fallback...")
    
    try:
        from .credentials import (
            UPSTOX_API_KEY as cred_api_key,
            UPSTOX_API_SECRET as cred_api_secret,
            UPSTOX_CLIENT_ID as cred_client_id,
            UPSTOX_TOTP_SECRET as cred_totp,
            FLASK_SECRET_KEY as cred_flask_key,
            SUPABASE_URL as cred_supabase_url,
            SUPABASE_KEY as cred_supabase_key
        )
        
        # Override with credentials.py values if env vars not set
        if not UPSTOX_API_KEY:
            UPSTOX_API_KEY = cred_api_key
        if not UPSTOX_API_SECRET:
            UPSTOX_API_SECRET = cred_api_secret
        if not UPSTOX_CLIENT_ID:
            UPSTOX_CLIENT_ID = cred_client_id
        if not UPSTOX_TOTP_SECRET:
            UPSTOX_TOTP_SECRET = cred_totp
        if not FLASK_SECRET_KEY:
            FLASK_SECRET_KEY = cred_flask_key
        if not SUPABASE_URL:
            SUPABASE_URL = cred_supabase_url
        if not SUPABASE_KEY:
            SUPABASE_KEY = cred_supabase_key
        
        print("✓ Successfully loaded credentials from config/credentials.py")
        
    except ImportError as e:
        print(f"✗ Failed to import from config/credentials.py: {e}")
        print("Please ensure you have either:")
        print("  1. .env file with required variables, OR")
        print("  2. config/credentials.py with required variables")