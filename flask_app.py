"""
Flask App for Upstox Supertrend - Render Deployment  
WITH REAL-TIME LOG STREAMING ENDPOINT
"""

from flask import Flask, request, jsonify, redirect, url_for, Response
import os
import sys
import json
import traceback
import threading
from datetime import datetime
import logging
from collections import deque

# ============================================================================
# FORCE UNBUFFERED OUTPUT FOR REAL-TIME LOGGING
# ============================================================================
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

# Import components
from auth.token_manager import TokenManager
from data_fetcher.instrument_mapper import InstrumentMapper
from data_fetcher.historical_data import HistoricalDataFetcher
from indicators.supertrend import SupertrendCalculator
from indicators.flat_base import FlatBaseDetector
from indicators.percentage_calculator import PercentageCalculator
from indicators.symbol_info_merger import SymbolInfoMerger
from storage.supabase_storage import SupabaseStorage

# ============================================================================
# LOGGING WITH BUFFER FOR STREAMING
# ============================================================================
logs_buffer = deque(maxlen=1000)  # Keep last 1000 log lines

class BufferingHandler(logging.Handler):
    """Custom log handler that stores logs in deque for streaming"""
    def emit(self, record):
        log_entry = self.format(record)
        logs_buffer.append(log_entry)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        BufferingHandler()
    ]
)

for handler in logging.getLogger().handlers:
    if hasattr(handler, 'flush'):
        handler.flush = lambda: sys.stdout.flush()

logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP INITIALIZATION
# ============================================================================
app = Flask(__name__)

# Initialize storage and auth
supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
supabase_storage.authenticate()

token_manager = TokenManager(
    token_file="upstox_token.json",
    use_supabase=True,
    supabase_storage=supabase_storage
)

# ============================================================================
# JOB STATUS TRACKING
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
    """Verify secret key"""
    return request.args.get('secret') == FLASK_SECRET_KEY

def get_error_response(error_message: str, error: Exception) -> dict:
    """Generate error response"""
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
# REAL-TIME LOG STREAMING ENDPOINT
# ============================================================================

@app.route('/logs')
def stream_logs():
    """
    Stream logs in real-time using Server-Sent Events (SSE)
    Access at: https://your-app.onrender.com/logs?secret=YOUR_SECRET
    """
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    def generate():
        """Generator function for SSE"""
        # Send existing logs first
        for log in list(logs_buffer):
            yield f"data: {log}\n\n"
        
        # Then stream new logs as they arrive
        last_size = len(logs_buffer)
        while True:
            import time
            time.sleep(0.5)  # Check every 500ms
            
            current_size = len(logs_buffer)
            if current_size > last_size:
                # New logs added
                new_logs = list(logs_buffer)[last_size:]
                for log in new_logs:
                    yield f"data: {log}\n\n"
                last_size = current_size
            elif current_size < last_size:
                # Buffer wrapped around (unlikely with maxlen=1000)
                last_size = current_size
    
    return Response(generate(), mimetype='text/event-stream')

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/login')
def login():
    """Login endpoint"""
    try:
        logger.info("=" * 60)
        logger.info("LOGIN REQUEST RECEIVED")
        logger.info("=" * 60)
        
        if not check_secret():
            logger.warning("Unauthorized login attempt")
            return jsonify({'error': 'Unauthorized'}), 401
        
        redirect_uri = UPSTOX_REDIRECT_URI
        oauth_url = (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={UPSTOX_API_KEY}"
            f"&redirect_uri={redirect_uri}"
            f"&state=upstox_auth_{int(datetime.now().timestamp())}"
        )
        
        logger.info(f"Redirecting to Upstox OAuth")
        return redirect(oauth_url)
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify(get_error_response("Login failed", e)), 500

@app.route('/callback')
def callback():
    """OAuth callback endpoint"""
    try:
        logger.info("=" * 60)
        logger.info("OAUTH CALLBACK RECEIVED")
        logger.info("=" * 60)
        
        auth_code = request.args.get('code')
        if not auth_code:
            raise Exception("No authorization code received")
        
        logger.info(f"Authorization code received: {auth_code[:10]}...")
        
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
        
        user_info = {
            "user_id": result.get('user_id'),
            "user_name": result.get('user_name'),
            "email": result.get('email'),
            "exchanges": result.get('exchanges', []),
            "products": result.get('products', []),
        }
        
        logger.info("✓ Access token obtained")
        logger.info(f"  User: {user_info['user_name']} ({user_info['user_id']})")
        
        token_data = {
            "access_token": access_token,
            "user_info": user_info,
            "timestamp": datetime.now().isoformat(),
            "expires_note": "Token expires at 3:30 AM IST next day"
        }
        
        logger.info("Saving token to Supabase...")
        success, message = supabase_storage.upload_token(token_data)
        
        if not success:
            raise Exception(f"Failed to save token: {message}")
        
        logger.info("✓ Token saved to Supabase")
        
        return f"""
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 50px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✓ Authentication Successful!</h1>
                <p>User: {user_info['user_name']}</p>
                <p>Token saved to Supabase Storage</p>
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
    """Check token status"""
    try:
        if not check_secret():
            return jsonify({'error': 'Unauthorized'}), 401
        
        exists, message = supabase_storage.check_token_exists()
        
        if not exists:
            return jsonify({
                'status': 'no_token',
                'message': message
            })
        
        if token_manager.load_token():
            is_valid = token_manager.validate_token()
            
            return jsonify({
                'status': 'exists',
                'valid': is_valid,
                'user': token_manager.user_info.get('user_id'),
                'timestamp': token_manager.token_timestamp
            })
        else:
            return jsonify({
                'status': 'exists_but_failed_to_load',
                'message': 'Token exists but failed to load'
            })
        
    except Exception as e:
        logger.error(f"Token status error: {e}")
        return jsonify(get_error_response("Token status check failed", e)), 500

# ============================================================================
# BACKGROUND JOB FUNCTION
# ============================================================================

def run_job_async():
    """Background job - runs complete pipeline"""
    global job_status
    
    sys.stdout.flush()
    sys.stderr.flush()
    
    try:
        job_status['running'] = True
        job_status['started_at'] = datetime.now().isoformat()
        job_status['last_status'] = 'running'
        job_status['last_error'] = None
        job_status['progress'] = {'stage': 'initializing'}
        
        logger.info("=" * 60)
        logger.info("🚀 ASYNC JOB STARTED")
        logger.info("=" * 60)
        sys.stdout.flush()
        
        # Step 1: Token
        logger.info("📋 Stage 1/7: Getting access token...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'authentication'}
        
        if not token_manager.load_token():
            raise Exception("Failed to load token")
        if not token_manager.validate_token():
            raise Exception("Token invalid or expired")
        
        access_token = token_manager.get_token()
        logger.info("✅ Token obtained")
        sys.stdout.flush()
        
        # Step 2: Instruments
        logger.info("📋 Stage 2/7: Fetching instruments...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'instruments'}
        
        symbol_merger = SymbolInfoMerger()
        if not symbol_merger.load_symbol_info():
            raise Exception("Failed to load symbol info")
        
        min_mcap = INSTRUMENT_FILTERS.get('min_market_cap', 5000)
        filtered_df = symbol_merger.symbol_info_df[symbol_merger.symbol_info_df['market_cap'] >= min_mcap]
        allowed_symbols = set(filtered_df['trading_symbol'].tolist())
        
        mapper = InstrumentMapper(access_token)
        instruments_dict = mapper.create_instrument_mapping(allowed_symbols)
        
        if not instruments_dict:
            raise Exception("Failed to create instrument mapping")
        
        logger.info(f"✅ Mapped {len(instruments_dict)} instruments")
        sys.stdout.flush()
        
        # Step 3: Historical data
        logger.info(f"📋 Stage 3/7: Fetching data for {len(instruments_dict)} instruments...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'fetching_data'}
        
        fetcher = HistoricalDataFetcher(access_token)
        historical_data = fetcher.fetch_instruments_data(instruments_dict, ['125min', 'daily'])
        
        if not historical_data:
            raise Exception("No historical data fetched")
        
        logger.info("✅ Data fetching completed")
        sys.stdout.flush()
        
        # Step 4: Calculate indicators
        logger.info("📋 Stage 4/7: Calculating indicators...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'indicators'}
        
        calculator = SupertrendCalculator()
        calculated_data = {}
        
        for timeframe, instruments_data in historical_data.items():
            configs = SUPERTREND_CONFIGS_125M if timeframe == '125min' else SUPERTREND_CONFIGS_DAILY
            calculated, _ = calculator.calculate_with_state_preservation(instruments_data, configs, timeframe)
            calculated_data[timeframe] = calculated
        
        logger.info("✅ Indicators calculated")
        sys.stdout.flush()
        
        # Step 4.5: Flat bases
        logger.info("📋 Stage 4.5/7: Detecting flat bases...")
        sys.stdout.flush()
        
        fb_detector = FlatBaseDetector()
        for timeframe in calculated_data.keys():
            configs = SUPERTREND_CONFIGS_125M if timeframe == '125min' else SUPERTREND_CONFIGS_DAILY
            calculated_data[timeframe] = fb_detector.calculate_flat_bases_for_symbols(calculated_data[timeframe], configs)
        
        logger.info("✅ Flat bases detected")
        sys.stdout.flush()
        
        # Step 5: Percentages
        logger.info("📋 Stage 5/7: Calculating percentages...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'percentages'}
        
        perc_calc = PercentageCalculator()
        with_percentages = {}
        
        for timeframe, data in calculated_data.items():
            configs = SUPERTREND_CONFIGS_125M if timeframe == '125min' else SUPERTREND_CONFIGS_DAILY
            with_percentages[timeframe] = perc_calc.process_timeframe_data(data, configs, timeframe)
        
        logger.info("✅ Percentages calculated")
        sys.stdout.flush()
        
        # Step 6: Merge symbol info
        logger.info("📋 Stage 6/7: Merging symbol info...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'merging'}
        
        final_merger = SymbolInfoMerger()
        final_data = final_merger.merge_all_timeframes(with_percentages)
        
        if not final_data:
            raise Exception("Failed to merge symbol info")
        
        logger.info("✅ Symbol info merged")
        sys.stdout.flush()
        
        # Step 7: Upload
        logger.info("📋 Stage 7/7: Uploading to Supabase...")
        sys.stdout.flush()
        job_status['progress'] = {'stage': 'uploading'}
        
        success = supabase_storage.upload_all_timeframes(final_data)
        
        if not success:
            raise Exception("Failed to upload to Supabase")
        
        logger.info("✅ Upload completed")
        sys.stdout.flush()
        
        # Success
        job_status['running'] = False
        job_status['last_run'] = datetime.now().isoformat()
        job_status['last_status'] = 'success'
        job_status['progress'] = {'stage': 'completed'}
        
        logger.info("=" * 60)
        logger.info("🎉 JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        sys.stdout.flush()
        
    except Exception as e:
        job_status['running'] = False
        job_status['last_run'] = datetime.now().isoformat()
        job_status['last_status'] = 'error'
        job_status['last_error'] = str(e)
        job_status['progress'] = {'stage': 'failed', 'error': str(e)}
        
        logger.error("=" * 60)
        logger.error(f"❌ JOB FAILED: {e}")
        logger.error("=" * 60)
        logger.error(traceback.format_exc())
        sys.stdout.flush()

# ============================================================================
# JOB ENDPOINTS
# ============================================================================

@app.route('/run-job')
def run_job():
    """Start job in background"""
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    global job_status
    
    if job_status['running']:
        return jsonify({
            'status': 'already_running',
            'message': 'Job already in progress'
        }), 409
    
    thread = threading.Thread(target=run_job_async, daemon=True)
    thread.start()
    
    logger.info("Background job started - check /logs for progress")
    sys.stdout.flush()
    
    return jsonify({
        'status': 'started',
        'message': 'Job started - view logs at /logs?secret=YOUR_SECRET',
        'started_at': job_status['started_at']
    }), 202

@app.route('/job-status')
def job_status_endpoint():
    """Check job status"""
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(job_status)

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)