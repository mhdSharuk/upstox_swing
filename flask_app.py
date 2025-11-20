"""
Flask App for Upstox Supertrend - PythonAnywhere Deployment
Handles OAuth authentication, token management via Supabase, and cron job execution
IMPORTANT: Uses NON-NUMBA indicator versions for PythonAnywhere compatibility
"""

from flask import Flask, request, jsonify, redirect, url_for
import os
import sys
import json
import traceback
import webbrowser
from datetime import datetime
import logging
import threading
from datetime import datetime

# Job status tracking
job_status = {
    'running': False,
    'last_run': None,
    'last_status': 'idle',
    'last_error': None,
    'progress': {}
}

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

# Import NON-NUMBA indicator versions (critical for PythonAnywhere)
from indicators.supertrend import SupertrendCalculator  # Non-Numba version
from indicators.flat_base import FlatBaseDetector      # Non-Numba version
from indicators.percentage_calculator import PercentageCalculator
from indicators.symbol_info_merger import SymbolInfoMerger

# Import storage
from storage.supabase_storage import SupabaseStorage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        'deployment': 'PythonAnywhere',
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
        
        # Save token to BOTH locations
        
        # 1. Save to Supabase Storage (for production cron jobs)
        logger.info("Saving token to Supabase Storage...")
        success_supabase, message_supabase = supabase_storage.upload_token(token_data)
        
        if not success_supabase:
            logger.error(f"Failed to save to Supabase: {message_supabase}")
            raise Exception("Failed to save token to Supabase")
        
        logger.info("✓ Token saved to Supabase")
        
        # 2. Save to local credentials folder (for local development)
        logger.info("Saving token to local credentials folder...")
        
        # Ensure credentials directory exists
        credentials_dir = os.path.join(APP_DIR, 'credentials')
        os.makedirs(credentials_dir, exist_ok=True)
        
        local_token_file = os.path.join(credentials_dir, 'upstox_token.json')
        
        try:
            with open(local_token_file, 'w') as f:
                json.dump(token_data, f, indent=4)
            logger.info(f"✓ Token saved to local file: {local_token_file}")
        except Exception as e:
            logger.warning(f"Failed to save to local file: {e}")
            # Don't fail if local save fails (production might not have write access)
        
        logger.info("=" * 60)
        logger.info("✓ AUTHENTICATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Token saved to:")
        logger.info(f"  1. Supabase: {supabase_storage.bucket_name}/credentials/upstox_token.json")
        logger.info(f"  2. Local: credentials/upstox_token.json")
        logger.info(f"Token valid until 3:30 AM IST next day")
        logger.info("=" * 60)
        
        # Return success HTML page
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                }}
                .success {{
                    color: #10b981;
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                h1 {{ color: #1f2937; margin-bottom: 10px; }}
                p {{ color: #6b7280; font-size: 16px; line-height: 1.6; }}
                .info {{ 
                    background: #f3f4f6; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin: 20px 0;
                    text-align: left;
                }}
                .info strong {{ color: #1f2937; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✓</div>
                <h1>Authentication Successful!</h1>
                <p>Your Upstox access token has been saved to Supabase Storage.</p>
                
                <div class="info">
                    <p><strong>User:</strong> {user_info['user_name']}</p>
                    <p><strong>User ID:</strong> {user_info['user_id']}</p>
                    <p><strong>Supabase Storage:</strong> {supabase_storage.bucket_name}/credentials/</p>
                    <p><strong>Local File:</strong> credentials/upstox_token.json</p>
                    <p><strong>Valid Until:</strong> 3:30 AM IST next day</p>
                </div>
                
                <p>You can close this window. Your cron jobs will now use this token automatically.</p>
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
# MAIN CRON JOB ENDPOINT - RUN PIPELINE
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
    def run_job_async():
        global job_status
        try:
            job_status['running'] = True
            job_status['started_at'] = datetime.now().isoformat()
            job_status['last_status'] = 'running'
            job_status['last_error'] = None
            job_status['progress'] = {'stage': 'initializing'}
            
            logger.info("=" * 60)
            logger.info("ASYNC JOB STARTED")
            logger.info("=" * 60)
            
            # Get token
            job_status['progress'] = {'stage': 'authentication', 'details': 'Getting access token'}
            access_token = token_manager.get_token()
            if not access_token:
                raise Exception("No valid access token available")
            
            # Get instruments
            job_status['progress'] = {'stage': 'instruments', 'details': 'Fetching instrument mappings'}
            symbol_merger = SymbolInfoMerger()
            if not symbol_merger.fetch_symbol_info():
                raise Exception("Failed to fetch symbol info")
            
            min_mcap = INSTRUMENT_FILTERS.get('min_market_cap', 5000)
            symbol_df = symbol_merger.symbol_info_df
            filtered_df = symbol_df[symbol_df['market_cap'] >= min_mcap]
            allowed_symbols = set(filtered_df['trading_symbol'].tolist())
            
            mapper = InstrumentMapper(access_token)
            instruments_dict = mapper.create_instrument_mapping(allowed_symbols)
            
            if not instruments_dict:
                raise Exception("Failed to create instrument mapping")
            
            logger.info(f"Mapped {len(instruments_dict)} instruments")
            
            # Fetch historical data
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
            
            # Calculate indicators
            job_status['progress'] = {'stage': 'indicators', 'details': 'Calculating indicators'}
            
            calculated_data = {}
            for timeframe, instruments_data in historical_data.items():
                if timeframe == '125min':
                    configs = SUPERTREND_CONFIGS_125M
                else:
                    configs = SUPERTREND_CONFIGS_DAILY
                
                calculator = SupertrendCalculator(configs)
                calculated_data[timeframe] = calculator.calculate_all_instruments(instruments_data)
            
            # Add percentages
            job_status['progress'] = {'stage': 'percentages', 'details': 'Calculating percentages'}
            
            perc_calc = PercentageCalculator()
            with_percentages = {}
            for timeframe, data in calculated_data.items():
                with_percentages[timeframe] = perc_calc.calculate_percentages(data)
            
            # Merge symbol info
            job_status['progress'] = {'stage': 'merging', 'details': 'Merging symbol information'}
            
            final_data = {}
            for timeframe, data in with_percentages.items():
                final_data[timeframe] = symbol_merger.merge_symbol_info(data)
            
            # Upload to Supabase
            job_status['progress'] = {'stage': 'uploading', 'details': 'Uploading to Supabase'}
            
            supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
            supabase_storage.authenticate()
            
            upload_results = {}
            for timeframe, data in final_data.items():
                result = supabase_storage.upload_dataframe(data, timeframe)
                upload_results[timeframe] = result
            
            # Success
            job_status['running'] = False
            job_status['last_run'] = datetime.now().isoformat()
            job_status['last_status'] = 'success'
            job_status['progress'] = {
                'stage': 'completed',
                'upload_results': upload_results,
                'instruments_processed': len(instruments_dict)
            }
            
            logger.info("=" * 60)
            logger.info("ASYNC JOB COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            
        except Exception as e:
            job_status['running'] = False
            job_status['last_run'] = datetime.now().isoformat()
            job_status['last_status'] = 'error'
            job_status['last_error'] = str(e)
            job_status['progress'] = {'stage': 'failed', 'error': str(e)}
            logger.error(f"Async job failed: {e}")
            logger.error(traceback.format_exc())
    
    # Start background thread
    thread = threading.Thread(target=run_job_async, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Job started in background',
        'started_at': job_status['started_at'],
        'check_status_at': '/job-status?secret=' + FLASK_SECRET_KEY
    }), 202


@app.route('/job-status')
def job_status_endpoint():
    """Check the status of the background job"""
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(job_status)
# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)