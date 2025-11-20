"""
Flask App for Upstox Supertrend - Render Deployment
Handles OAuth authentication, token management via Supabase, and cron job execution
UPDATED: Background threading with real-time logging for long-running jobs
CORRECTED: All method names verified against actual class implementations
IMPORTANT: Uses NON-NUMBA indicator versions for compatibility
"""

from flask import Flask, request, jsonify, redirect, url_for
import os
import sys
import json
import traceback
import threading
from datetime import datetime
import logging

# ============================================================================
# FORCE UNBUFFERED OUTPUT FOR REAL-TIME LOGGING
# ============================================================================
# This ensures logs appear immediately in Render dashboard
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Get absolute path of app directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Import configuration
from config.env_loader import (
    UPSTOX_API_KEY,
    UPSTOX_API_SECRET,
    UPSTOX_TOTP_SECRET,
    FLASK_SECRET_KEY,
    SUPABASE_URL,
    SUPABASE_KEY,
    UPSTOX_REDIRECT_URI
)
from config.settings import (
    SUPERTREND_CONFIGS_125M,
    SUPERTREND_CONFIGS_DAILY,
    INSTRUMENT_FILTERS
)

# Import auth components
from auth.token_manager import TokenManager
from auth.upstox_auth import UpstoxAuthenticator

# Import data components
from data_fetcher.instrument_mapper import InstrumentMapper
from data_fetcher.historical_data import HistoricalDataFetcher

# Import NON-NUMBA indicator versions (critical for compatibility)
from indicators.supertrend import SupertrendCalculator
from indicators.flat_base import FlatBaseDetector
from indicators.percentage_calculator import PercentageCalculator
from indicators.symbol_info_merger import SymbolInfoMerger

# Import storage
from storage.supabase_storage import SupabaseStorage

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Force immediate flush on log handlers
for handler in logging.getLogger().handlers:
    handler.flush = lambda: sys.stdout.flush()

logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================
app = Flask(__name__)

# Initialize Supabase Storage (for token and parquet files)
supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
supabase_storage.authenticate()

# Initialize Token Manager with Supabase
token_manager = TokenManager(
    token_file="upstox_token.json",  # Not used, but kept for compatibility
    use_supabase=True,
    supabase_storage=supabase_storage
)

# ============================================================================
# JOB STATUS TRACKING (In-Memory)
# ============================================================================
job_status = {
    'running': False,
    'started_at': None,
    'last_run': None,
    'last_status': 'idle',
    'last_error': None,
    'progress': {}
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def check_secret():
    """Verify secret key for protected endpoints"""
    return request.args.get('secret') == FLASK_SECRET_KEY


def get_error_response(error_message: str, error: Exception) -> dict:
    """Generate error response with traceback"""
    return {
        'status': 'error',
        'message': error_message,
        'error': str(error),
        'traceback': traceback.format_exc(),
        'timestamp': datetime.now().isoformat()
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'app': 'Upstox Supertrend Flask App',
        'deployment': 'Render',
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/login')
def login():
    """
    Login endpoint - Redirects to Upstox OAuth page
    User manually enters TOTP from authenticator app
    """
    try:
        logger.info("=" * 60)
        logger.info("LOGIN REQUEST RECEIVED")
        logger.info("=" * 60)
        
        # Check if secret is provided
        if not check_secret():
            logger.warning("Unauthorized login attempt - invalid secret")
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Generate Upstox OAuth URL
        redirect_uri = UPSTOX_REDIRECT_URI
        
        # Build OAuth URL
        oauth_url = (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={UPSTOX_API_KEY}"
            f"&redirect_uri={redirect_uri}"
            f"&state=upstox_auth_{int(datetime.now().timestamp())}"
        )
        
        logger.info(f"Redirecting to Upstox OAuth: {oauth_url}")
        logger.info("User will manually enter TOTP from authenticator app")
        
        # Redirect to Upstox OAuth page
        return redirect(oauth_url)
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify(get_error_response("Login failed", e)), 500


@app.route('/callback')
def callback():
    """
    OAuth callback endpoint - Receives authorization code from Upstox
    Exchanges code for access token and saves to Supabase
    """
    try:
        logger.info("=" * 60)
        logger.info("OAUTH CALLBACK RECEIVED")
        logger.info("=" * 60)
        
        # Get authorization code from query params
        auth_code = request.args.get('code')
        
        if not auth_code:
            error_msg = "No authorization code received"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 400
        
        logger.info(f"Authorization code received: {auth_code[:10]}...")
        
        # Exchange code for access token
        logger.info("Exchanging authorization code for access token...")
        
        url = "https://api.upstox.com/v2/login/authorization/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "code": auth_code,
            "client_id": UPSTOX_API_KEY,
            "client_secret": UPSTOX_API_SECRET,
            "redirect_uri": UPSTOX_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        import requests
        response = requests.post(url, headers=headers, data=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        access_token = result.get("access_token")
        
        if not access_token:
            raise Exception("No access token in response")
        
        # Store user info
        user_info = {
            "user_id": result.get('user_id'),
            "user_name": result.get('user_name'),
            "email": result.get('email'),
            "exchanges": result.get('exchanges', []),
            "products": result.get('products', []),
        }
        
        logger.info("✓ Access token obtained successfully")
        logger.info(f"  User: {user_info['user_name']} ({user_info['user_id']})")
        
        # Prepare token data
        token_data = {
            "access_token": access_token,
            "user_info": user_info,
            "timestamp": datetime.now().isoformat(),
            "expires_note": "Token expires at 3:30 AM IST next day"
        }
        
        # Save token to Supabase Storage (for production cron jobs)
        logger.info("Saving token to Supabase Storage...")
        success_supabase, message_supabase = supabase_storage.upload_token(token_data)
        
        if not success_supabase:
            logger.error(f"Failed to save to Supabase: {message_supabase}")
            raise Exception("Failed to save token to Supabase")
        
        logger.info("✓ Token saved to Supabase")
        
        # Success HTML response
        return f"""
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #28a745; }}
                .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .code {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-family: monospace; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✓ Authentication Successful!</h1>
                <div class="info">
                    <p><strong>User:</strong> {user_info['user_name']}</p>
                    <p><strong>User ID:</strong> {user_info['user_id']}</p>
                    <p><strong>Email:</strong> {user_info.get('email', 'N/A')}</p>
                </div>
                <h3>Token Storage:</h3>
                <p>✓ Token saved to Supabase Storage</p>
                <p class="code">{message_supabase}</p>
                <h3>What's Next?</h3>
                <p>Your access token is now stored securely in Supabase Storage.</p>
                <p>Your cron jobs will now use this token automatically.</p>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        logger.error(traceback.format_exc())
        return jsonify(get_error_response("OAuth callback failed", e)), 500


# ============================================================================
# TOKEN STATUS ENDPOINT
# ============================================================================

@app.route('/token-status')
def token_status():
    """Check token existence and validity"""
    try:
        if not check_secret():
            return jsonify({'error': 'Unauthorized'}), 401
        
        # Check if token exists in Supabase
        exists, message = supabase_storage.check_token_exists()
        
        if not exists:
            return jsonify({
                'status': 'no_token',
                'message': message,
                'storage': 'Supabase'
            })
        
        # Try to load and validate token
        if token_manager.load_token():
            is_valid = token_manager.validate_token()
            
            return jsonify({
                'status': 'exists',
                'valid': is_valid,
                'user': token_manager.user_info.get('user_id'),
                'timestamp': token_manager.token_timestamp,
                'storage': 'Supabase'
            })
        else:
            return jsonify({
                'status': 'exists_but_failed_to_load',
                'message': 'Token exists in Supabase but failed to load',
                'storage': 'Supabase'
            })
        
    except Exception as e:
        logger.error(f"Token status error: {e}")
        return jsonify(get_error_response("Token status check failed", e)), 500


# ============================================================================
# BACKGROUND JOB FUNCTION
# ============================================================================

def run_job_async():
    """
    Background job function - runs the complete pipeline
    Logs are flushed immediately for real-time visibility
    ALL METHOD NAMES CORRECTED TO MATCH ACTUAL IMPLEMENTATIONS
    """
    global job_status
    
    # Force unbuffered logging
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        job_status['running'] = True
        job_status['started_at'] = datetime.now().isoformat()
        job_status['last_status'] = 'running'
        job_status['last_error'] = None
        job_status['progress'] = {'stage': 'initializing'}
        
        # IMMEDIATE LOG - should appear right away
        logger.info("=" * 60)
        logger.info("🚀 ASYNC JOB STARTED - BACKGROUND THREAD ACTIVE")
        logger.info("=" * 60)
        sys.stdout.flush()
        
        # Step 1: Get token
        logger.info("📋 Stage 1/7: Getting access token...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'authentication', 'details': 'Getting access token'}
        
        if not token_manager.load_token():
            raise Exception("Failed to load token from Supabase")
        
        if not token_manager.validate_token():
            raise Exception("Token is invalid or expired")
        
        access_token = token_manager.get_token()
        logger.info("✅ Token obtained successfully")
        sys.stdout.flush()
        
        # Step 2: Get instruments
        logger.info("📋 Stage 2/7: Fetching instrument mappings...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'instruments', 'details': 'Fetching instrument mappings'}
        
        symbol_merger = SymbolInfoMerger()
        
        # CORRECTED: Use load_symbol_info() not fetch_symbol_info()
        if not symbol_merger.load_symbol_info():
            raise Exception("Failed to load symbol info CSV")
        
        min_mcap = INSTRUMENT_FILTERS.get('min_market_cap', 5000)
        symbol_df = symbol_merger.symbol_info_df
        filtered_df = symbol_df[symbol_df['market_cap'] >= min_mcap].head(50)
        allowed_symbols = set(filtered_df['trading_symbol'].tolist())
        
        mapper = InstrumentMapper(access_token)
        instruments_dict = mapper.create_instrument_mapping(allowed_symbols)
        
        if not instruments_dict:
            raise Exception("Failed to create instrument mapping")
        
        logger.info(f"✅ Mapped {len(instruments_dict)} instruments")
        sys.stdout.flush()
        
        # Step 3: Fetch historical data
        logger.info(f"📋 Stage 3/7: Fetching data for {len(instruments_dict)} instruments...")
        logger.info("   This will take 15-25 minutes... (longest stage)")
        sys.stdout.flush()
        job_status['progress'] = {
            'stage': 'fetching_data', 
            'details': f'Fetching data for {len(instruments_dict)} instruments',
            'instruments_total': len(instruments_dict)
        }
        
        fetcher = HistoricalDataFetcher(access_token)
        timeframes = ['125min', 'daily']
        historical_data = fetcher.fetch_instruments_data(instruments_dict, timeframes)
        
        if not historical_data:
            raise Exception("No historical data fetched")
        
        logger.info("✅ Data fetching completed")
        sys.stdout.flush()
        
        # Step 4: Calculate indicators
        logger.info("📋 Stage 4/7: Calculating indicators...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'indicators', 'details': 'Calculating indicators'}
        
        # CORRECTED: SupertrendCalculator takes NO arguments
        calculator = SupertrendCalculator()
        calculated_data = {}
        state_variables = {}
        
        for timeframe, instruments_data in historical_data.items():
            if timeframe == '125min':
                configs = SUPERTREND_CONFIGS_125M
            else:
                configs = SUPERTREND_CONFIGS_DAILY
            
            # CORRECTED: Use calculate_with_state_preservation()
            calculated, states = calculator.calculate_with_state_preservation(
                instruments_data,
                configs,
                timeframe
            )
            calculated_data[timeframe] = calculated
            state_variables[timeframe] = states
        
        logger.info("✅ Indicators calculated")
        sys.stdout.flush()
        
        # Step 4.5: Detect flat bases
        logger.info("📋 Stage 4.5/7: Detecting flat bases...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'flat_bases', 'details': 'Detecting flat base patterns'}
        
        fb_detector = FlatBaseDetector()
        for timeframe in calculated_data.keys():
            if timeframe == '125min':
                configs = SUPERTREND_CONFIGS_125M
            else:
                configs = SUPERTREND_CONFIGS_DAILY
            
            # CORRECTED: Use calculate_flat_bases_for_symbols()
            calculated_data[timeframe] = fb_detector.calculate_flat_bases_for_symbols(
                calculated_data[timeframe],
                configs
            )
        
        logger.info("✅ Flat bases detected")
        sys.stdout.flush()
        
        # Step 5: Add percentages
        logger.info("📋 Stage 5/7: Calculating percentages...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'percentages', 'details': 'Calculating percentages'}
        
        perc_calc = PercentageCalculator()
        with_percentages = {}
        
        for timeframe, data in calculated_data.items():
            if timeframe == '125min':
                configs = SUPERTREND_CONFIGS_125M
            else:
                configs = SUPERTREND_CONFIGS_DAILY
            
            # CORRECTED: Use process_timeframe_data() not calculate_percentages()
            with_percentages[timeframe] = perc_calc.process_timeframe_data(
                data,
                configs,
                timeframe
            )
        
        logger.info("✅ Percentages calculated")
        sys.stdout.flush()
        
        # Step 6: Merge symbol info
        logger.info("📋 Stage 6/7: Merging symbol information...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'merging', 'details': 'Merging symbol information'}
        
        # Symbol info already loaded in Step 2, so just create new instance and merge
        final_symbol_merger = SymbolInfoMerger()
        final_data = final_symbol_merger.merge_all_timeframes(with_percentages)
        
        if not final_data:
            raise Exception("Failed to merge symbol info")
        
        logger.info("✅ Symbol info merged")
        sys.stdout.flush()
        
        # Step 7: Upload to Supabase
        logger.info("📋 Stage 7/7: Uploading to Supabase...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'uploading', 'details': 'Uploading to Supabase'}
        
        # CORRECTED: Use upload_all_timeframes() which internally calls upload_parquet()
        success = supabase_storage.upload_all_timeframes(final_data)
        
        if not success:
            raise Exception("Failed to upload parquet files to Supabase")
        
        logger.info("✅ Upload completed")
        sys.stdout.flush()
        
        # Success
        job_status['running'] = False
        job_status['last_run'] = datetime.now().isoformat()
        job_status['last_status'] = 'success'
        job_status['progress'] = {
            'stage': 'completed',
            'instruments_processed': len(instruments_dict),
            'timeframes': list(final_data.keys())
        }
        
        logger.info("=" * 60)
        logger.info("🎉 ASYNC JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"Total instruments processed: {len(instruments_dict)}")
        logger.info(f"Timeframes: {list(final_data.keys())}")
        logger.info("=" * 60)
        sys.stdout.flush()
        
    except Exception as e:
        job_status['running'] = False
        job_status['last_run'] = datetime.now().isoformat()
        job_status['last_status'] = 'error'
        job_status['last_error'] = str(e)
        job_status['progress'] = {'stage': 'failed', 'error': str(e)}
        
        logger.error("=" * 60)
        logger.error(f"❌ ASYNC JOB FAILED: {e}")
        logger.error("=" * 60)
        logger.error(traceback.format_exc())
        sys.stdout.flush()
        sys.stderr.flush()


# ============================================================================
# MAIN CRON JOB ENDPOINT - ASYNC VERSION
# ============================================================================

@app.route('/run-job')
def run_job():
    """
    Run the main data pipeline job - ASYNC VERSION
    Starts job in background thread and returns immediately
    """
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    global job_status
    
    # Check if job is already running
    if job_status['running']:
        return jsonify({
            'status': 'already_running',
            'message': 'Job is already in progress',
            'started_at': job_status.get('started_at'),
            'progress': job_status.get('progress', {})
        }), 409
    
    # Start job in background thread
    thread = threading.Thread(target=run_job_async, daemon=True)
    thread.start()
    
    logger.info("Background job thread started - check logs for real-time progress")
    sys.stdout.flush()
    
    return jsonify({
        'status': 'started',
        'message': 'Job started in background',
        'started_at': job_status['started_at'],
        'check_status_at': f'/job-status?secret={FLASK_SECRET_KEY}'
    }), 202


@app.route('/job-status')
def job_status_endpoint():
    """Check the status of the background job"""
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(job_status)


# ============================================================================
# DEBUG ENDPOINT (OPTIONAL - FOR TESTING)
# ============================================================================

@app.route('/debug-thread')
def debug_thread():
    """Debug endpoint to verify threading and logging works"""
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    import time
    
    def test_thread():
        for i in range(5):
            print(f"DEBUG: Thread iteration {i}", flush=True)
            logger.info(f"DEBUG: Thread iteration {i}")
            sys.stdout.flush()
            time.sleep(1)
        logger.info("DEBUG: Thread completed")
        sys.stdout.flush()
    
    thread = threading.Thread(target=test_thread, daemon=True)
    thread.start()
    
    return jsonify({'status': 'test thread started, check logs for output'})


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    # Run with unbuffered output
    app.run(host='0.0.0.0', port=5000, debug=False)