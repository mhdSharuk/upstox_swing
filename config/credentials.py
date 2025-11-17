UPSTOX_API_KEY = "cba4328f-64cc-4a56-93ad-3ae381c50d14"
UPSTOX_API_SECRET = "m3p4res4lt"
UPSTOX_REDIRECT_URI = "http://127.0.0.1:8000/callback"
UPSTOX_CLIENT_ID = "FY3773"
UPSTOX_TOTP_SECRET = "2UEICJVQYID23W4GQ7263PWIFPSB2DMM"
GOOGLE_SHEET_ID = "1c2D3KERJJSJIDRO6hzVVsiasAN3uXyypESMkThxWVZo"
SERVICE_ACCOUNT_FILE = "service_account.json"
FLASK_SECRET_KEY = "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY_USING_COMMAND_ABOVE"

# ==================== FLASK APP CONFIGURATION ====================
# Flask Secret Key: Used to secure API endpoints
# Generate a secure random key with:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
# 
# IMPORTANT: Change this to a random secret value!
FLASK_SECRET_KEY = "w0AgVxkN3dxeOYvc5B8jq4bQ3t8AsEXWHtVUhl4UyTQ"

# Webhook URL: This is where Upstox will send the access token after approval
# Format: https://YOUR_PYTHONANYWHERE_USERNAME.pythonanywhere.com/upstox-webhook
# 
# For user 'mhdSharuk', the webhook URL is:
WEBHOOK_URL = "https://mhdsharuk.pythonanywhere.com/upstox-webhook"

# ==================== DEPLOYMENT CONFIGURATION ====================
# PythonAnywhere Username (for reference only)
PYTHONANYWHERE_USERNAME = "mhdsharuk"

# Base URL for your deployed Flask app
FLASK_BASE_URL = f"https://{PYTHONANYWHERE_USERNAME}.pythonanywhere.com"

# ==================== NOTES ====================
"""
SETUP CHECKLIST:

1. Upstox Configuration:
   ✓ Create app at https://account.upstox.com/developer/apps
   ✓ Copy API Key and API Secret
   ✓ Setup TOTP (Time-based OTP) in Upstox account
   ✓ Configure Notifier Webhook URL in Upstox app settings
   
2. Google Sheets Configuration:
   ✓ Create a Google Cloud project
   ✓ Enable Google Sheets API and Google Drive API
   ✓ Create a service account and download JSON key
   ✓ Share your Google Sheet with the service account email (Editor access)
   ✓ Copy the Sheet ID from the URL
   
3. Flask App Configuration:
   ✓ Generate a secure FLASK_SECRET_KEY
   ✓ Update WEBHOOK_URL with your PythonAnywhere username
   ✓ Configure this webhook URL in Upstox app settings
   
4. PythonAnywhere Setup:
   ✓ Upload all project files
   ✓ Install requirements: pip install --user -r requirements.txt
   ✓ Configure Flask web app
   ✓ Test endpoints
   
5. cron-job.org Setup:
   ✓ Create account at https://cron-job.org
   ✓ Configure token request job (8:00 AM IST)
   ✓ Configure retry jobs (8:30 AM, 9:00 AM IST)
   ✓ Configure data fetch jobs (9:15 AM, 11:20 AM, 1:25 PM, 3:30 PM IST)

IMPORTANT SECURITY NOTES:
- Never commit this file to git!
- Add 'config/credentials.py' to .gitignore
- Keep FLASK_SECRET_KEY secure and random
- Don't share service_account.json file
"""