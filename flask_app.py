"""
Flask Application for Upstox Supertrend - PythonAnywhere Deployment
Handles token requests, webhook callbacks, and scheduled job execution

UPDATED: Now uses environment variables via config.env_loader
"""

from flask import Flask, request, jsonify
import os
import sys
import json
import requests
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules - NOW USING ENV_LOADER
from config.env_loader import (
    UPSTOX_API_KEY,
    UPSTOX_API_SECRET,
    FLASK_SECRET_KEY,
    UPSTOX_CLIENT_ID
)
from auth.token_manager import TokenManager
from main import UpstoxSupertrendPipeline

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_SECRET_KEY

# Initialize token manager
token_manager = TokenManager()


# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

def verify_secret_token():
    """Verify that requests include the correct secret token"""
    provided_token = request.args.get('secret') or request.headers.get('X-Secret-Token')
    
    if not provided_token:
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
        return False
    
    if provided_token != FLASK_SECRET_KEY:
        logger.warning(f"Invalid secret token from {request.remote_addr}")
        return False
    
    return True


# ============================================================================
# ENDPOINT 1: HEALTH CHECK
# ============================================================================

@app.route('/')
@app.route('/health')
def health_check():
    """Health check endpoint - No authentication required"""
    return jsonify({
        'status': 'running',
        'app': 'Upstox Supertrend Pipeline',
        'timestamp': datetime.now().isoformat(),
        'config_source': 'environment_variables',
        'endpoints': {
            'health': '/health',
            'request_token': '/request-token?secret=YOUR_SECRET',
            'webhook': '/upstox-webhook',
            'run_job': '/run-job?secret=YOUR_SECRET',
            'token_status': '/token-status?secret=YOUR_SECRET'
        }
    }), 200


# ============================================================================
# ENDPOINT 2: REQUEST NEW TOKEN (Called by cron-job.org)
# ============================================================================

@app.route('/request-token', methods=['GET', 'POST'])
def request_token():
    """
    Request a new access token from Upstox
    This triggers a notification to the user's mobile app
    
    Called by: cron-job.org at 8:00 AM daily (and retries)
    """
    # Verify authentication
    if not verify_secret_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    logger.info("=" * 60)
    logger.info("TOKEN REQUEST INITIATED")
    logger.info("=" * 60)
    
    try:
        # Call Upstox Access Token Request API
        url = f"https://api.upstox.com/v2/login/authorization/token/request/{UPSTOX_CLIENT_ID}"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "client_secret": UPSTOX_API_SECRET
        }
        
        logger.info(f"Requesting token from Upstox API...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            logger.info("✓ Token request sent successfully!")
            logger.info(f"Authorization expires at: {data.get('data', {}).get('authorization_expiry', 'N/A')}")
            logger.info("📱 CHECK YOUR PHONE for Upstox notification")
            logger.info("💬 You should receive WhatsApp + App notification")
            logger.info("👆 Tap 'Approve' to authorize the token")
            
            return jsonify({
                'status': 'success',
                'message': 'Token request sent to Upstox. Please approve on your mobile.',
                'timestamp': datetime.now().isoformat(),
                'authorization_expiry': data.get('data', {}).get('authorization_expiry'),
                'next_step': 'Check your phone and tap Approve in Upstox app'
            }), 200
        
        else:
            error_data = response.json() if response.text else {}
            logger.error(f"✗ Token request failed: {response.status_code}")
            logger.error(f"Response: {error_data}")
            
            return jsonify({
                'status': 'error',
                'message': 'Failed to request token from Upstox',
                'error_code': response.status_code,
                'error_details': error_data
            }), 500
    
    except requests.exceptions.Timeout:
        logger.error("✗ Request timeout - Upstox API not responding")
        return jsonify({
            'status': 'error',
            'message': 'Timeout connecting to Upstox API'
        }), 504
    
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT 3: WEBHOOK (Called by Upstox after user approval)
# ============================================================================

@app.route('/upstox-webhook', methods=['POST'])
def upstox_webhook():
    """
    Webhook endpoint to receive access token from Upstox
    This is called automatically after user approves the token request
    
    Called by: Upstox API (after user taps Approve)
    """
    logger.info("=" * 60)
    logger.info("WEBHOOK CALLBACK RECEIVED FROM UPSTOX")
    logger.info("=" * 60)
    
    try:
        # Get JSON payload
        data = request.get_json()
        
        if not data:
            logger.error("✗ No JSON data received")
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        logger.info(f"Webhook payload received: {json.dumps(data, indent=2)}")
        
        # Verify it's an access token message
        if data.get('message_type') != 'access_token':
            logger.warning(f"✗ Unknown message type: {data.get('message_type')}")
            return jsonify({'status': 'error', 'message': 'Invalid message type'}), 400
        
        # Extract token and user info
        access_token = data.get('access_token')
        user_id = data.get('user_id')
        issued_at = data.get('issued_at')
        expires_at = data.get('expires_at')
        
        if not access_token:
            logger.error("✗ No access token in webhook payload")
            return jsonify({'status': 'error', 'message': 'No access token provided'}), 400
        
        # Create user info dict
        user_info = {
            'user_id': user_id,
            'user_name': user_id,  # Webhook doesn't provide full user info
            'email': '',
            'issued_at': issued_at,
            'expires_at': expires_at
        }
        
        # Save token using TokenManager
        success = token_manager.save_token(access_token, user_info)
        
        if success:
            logger.info("=" * 60)
            logger.info("✓ TOKEN SAVED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"User ID: {user_id}")
            logger.info(f"Issued at: {issued_at}")
            logger.info(f"Expires at: {expires_at}")
            logger.info(f"Token saved to: {token_manager.token_file}")
            logger.info("✓ Ready for scheduled jobs!")
            logger.info("=" * 60)
            
            return jsonify({
                'status': 'success',
                'message': 'Token received and saved successfully',
                'user_id': user_id,
                'issued_at': issued_at,
                'expires_at': expires_at
            }), 200
        else:
            logger.error("✗ Failed to save token to file")
            return jsonify({
                'status': 'error',
                'message': 'Failed to save token'
            }), 500
    
    except Exception as e:
        logger.error(f"✗ Error processing webhook: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error processing webhook: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINT 4: RUN MAIN JOB (Called by cron-job.org during market hours)
# ============================================================================

@app.route('/run-job', methods=['GET', 'POST'])
def run_job():
    """
    Execute the main Upstox Supertrend pipeline
    Fetches data, calculates indicators, writes to Google Sheets
    
    Called by: cron-job.org at 9:15 AM, 11:20 AM, 1:25 PM, 3:30 PM IST
    """
    # Verify authentication
    if not verify_secret_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    logger.info("=" * 60)
    logger.info("SCHEDULED JOB EXECUTION STARTED")
    logger.info("=" * 60)
    logger.info(f"Triggered at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    
    try:
        # Check if token exists and is valid
        if not token_manager.load_token():
            logger.error("✗ No valid token found!")
            return jsonify({
                'status': 'error',
                'message': 'No valid token available. Token request may not have been approved yet.',
                'suggestion': 'Check if you approved the token request on your mobile device'
            }), 400
        
        # Validate token
        if not token_manager.validate_token():
            logger.error("✗ Token is invalid or expired!")
            return jsonify({
                'status': 'error',
                'message': 'Token is invalid or expired',
                'suggestion': 'Wait for next token request or manually trigger /request-token'
            }), 400
        
        logger.info("✓ Token validated successfully")
        logger.info(f"User: {token_manager.user_info.get('user_id')}")
        
        # Execute the main pipeline
        logger.info("\n🚀 Starting Upstox Supertrend Pipeline...")
        
        pipeline = UpstoxSupertrendPipeline()
        
        # Set the access token
        pipeline.access_token = token_manager.get_token()
        
        # Run pipeline (skip step 0 and step 1 since token is already validated)
        logger.info("Step 0: Skipping Google Sheets test (already verified)")
        
        if not pipeline.step2_fetch_instruments():
            raise Exception("Failed at Step 2: Fetch Instruments")
        
        if not pipeline.step3_fetch_historical_data():
            raise Exception("Failed at Step 3: Fetch Historical Data")
        
        if not pipeline.step4_calculate_supertrends():
            raise Exception("Failed at Step 4: Calculate Supertrends")
        
        if not pipeline.step5_detect_flat_bases():
            raise Exception("Failed at Step 5: Detect Flat Bases")
        
        # Initialize sheets writer if not already done
        if not pipeline.sheets_writer:
            from config.env_loader import GOOGLE_SHEET_ID, SERVICE_ACCOUNT_FILE
            from storage.sheets_writer import GoogleSheetsWriter
            pipeline.sheets_writer = GoogleSheetsWriter(GOOGLE_SHEET_ID, SERVICE_ACCOUNT_FILE)
            if not pipeline.sheets_writer.authenticate():
                raise Exception("Failed to authenticate with Google Sheets")
        
        if not pipeline.step6_save_to_google_sheets():
            raise Exception("Failed at Step 6: Save to Google Sheets")
        
        logger.info("=" * 60)
        logger.info("✓ JOB COMPLETED SUCCESSFULLY!")
        logger.info("=" * 60)
        
        return jsonify({
            'status': 'success',
            'message': 'Pipeline executed successfully',
            'timestamp': datetime.now().isoformat(),
            'instruments_processed': len(pipeline.instruments_dict),
            'spreadsheet_url': f'https://docs.google.com/spreadsheets/d/{pipeline.sheets_writer.sheet_id}'
        }), 200
    
    except Exception as e:
        logger.error(f"✗ Job execution failed: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Job execution failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500


# ============================================================================
# ENDPOINT 5: TOKEN STATUS (Check token validity)
# ============================================================================

@app.route('/token-status', methods=['GET'])
def token_status():
    """
    Check the current token status
    Useful for debugging and monitoring
    """
    # Verify authentication
    if not verify_secret_token():
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Try to load token
        token_loaded = token_manager.load_token()
        
        if not token_loaded:
            return jsonify({
                'status': 'no_token',
                'message': 'No token file found',
                'token_file': token_manager.token_file,
                'action_required': 'Request a new token via /request-token'
            }), 200
        
        # Check if token is valid
        is_valid = token_manager.validate_token()
        is_expired = token_manager.is_token_likely_expired()
        
        return jsonify({
            'status': 'token_exists',
            'is_valid': is_valid,
            'is_likely_expired': is_expired,
            'user_id': token_manager.user_info.get('user_id', 'N/A'),
            'user_name': token_manager.user_info.get('user_name', 'N/A'),
            'token_timestamp': token_manager.token_timestamp,
            'token_file': token_manager.token_file,
            'note': 'Token expires at 3:30 AM IST next day'
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking token status: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Error checking token status: {str(e)}'
        }), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/',
            '/health',
            '/request-token',
            '/upstox-webhook',
            '/run-job',
            '/token-status'
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # For local testing only
    # PythonAnywhere will run this via WSGI
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)