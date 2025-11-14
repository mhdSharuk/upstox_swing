"""
Flask App for Upstox Supertrend
Simple implementation following Upstox API documentation exactly
"""

from flask import Flask, request, jsonify
import os
import sys
import requests
from datetime import datetime
import logging

# Get absolute path of app directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from config.env_loader import UPSTOX_API_KEY, UPSTOX_API_SECRET, FLASK_SECRET_KEY
from auth.token_manager import TokenManager
from main import UpstoxSupertrendPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize TokenManager with absolute path
TOKEN_FILE = os.path.join(APP_DIR, 'upstox_token.json')
token_manager = TokenManager(token_file=TOKEN_FILE)


# Log ALL incoming requests
@app.before_request
def log_all_requests():
    logger.info(f"===== INCOMING REQUEST =====")
    logger.info(f"Method: {request.method}")
    logger.info(f"Path: {request.path}")
    logger.info(f"Full URL: {request.url}")
    if request.method == 'POST':
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body: {request.get_data(as_text=True)}")
    logger.info(f"============================")


def check_secret():
    return request.args.get('secret') == FLASK_SECRET_KEY


@app.route('/')
def health():
    return jsonify({'status': 'running'})


@app.route('/request-token')
def request_token():
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    url = f"https://api.upstox.com/v3/login/auth/token/request/{UPSTOX_API_KEY}"

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json={"client_secret": UPSTOX_API_SECRET},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            logger.info("Token request sent! Check your phone.")
            return jsonify({
                'status': 'success',
                'message': 'Check your phone for Upstox notification',
                'data': data
            })
        else:
            logger.error(f"API returned {response.status_code}: {response.text}")
            return jsonify({
                'status': 'error',
                'code': response.status_code,
                'response': response.json() if response.text else {}
            }), response.status_code

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/upstox-webhook-v2', methods=['POST'])
def webhook():
    try:
        logger.info('Trying to access /upstox-webhook-v2')
        data = request.get_json()
        logger.info(f"Webhook received: {data}")

        if data.get('message_type') == 'access_token':
            token = data.get('access_token')
            user_id = data.get('user_id')

            user_info = {
                'user_id': user_id,
                'user_name': user_id,
                'email': '',
                'issued_at': data.get('issued_at'),
                'expires_at': data.get('expires_at')
            }

            token_manager.save_token(token, user_info)
            logger.info(f"Token saved for {user_id}")
            return jsonify({'status': 'success'})

        return jsonify({'status': 'invalid'}), 400

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500


@app.route('/token-status')
def token_status():
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    if token_manager.load_token():
        return jsonify({
            'status': 'exists',
            'valid': token_manager.validate_token(),
            'user': token_manager.user_info.get('user_id')
        })
    return jsonify({'status': 'no_token'})


@app.route('/run-job')
def run_job():
    if not check_secret():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        if not token_manager.load_token() or not token_manager.validate_token():
            return jsonify({'error': 'No valid token'}), 400

        logger.info("Starting pipeline...")
        pipeline = UpstoxSupertrendPipeline()
        pipeline.access_token = token_manager.get_token()

        if not pipeline.step2_fetch_instruments():
            raise Exception("Fetch instruments failed")
        if not pipeline.step3_fetch_historical_data():
            raise Exception("Fetch data failed")
        if not pipeline.step4_calculate_supertrends():
            raise Exception("Calculate supertrends failed")
        if not pipeline.step5_detect_flat_bases():
            raise Exception("Detect flat bases failed")

        if not pipeline.sheets_writer:
            from config.env_loader import GOOGLE_SHEET_ID, SERVICE_ACCOUNT_FILE
            from storage.sheets_writer import GoogleSheetsWriter
            pipeline.sheets_writer = GoogleSheetsWriter(GOOGLE_SHEET_ID, SERVICE_ACCOUNT_FILE)
            pipeline.sheets_writer.authenticate()

        if not pipeline.step6_save_to_google_sheets():
            raise Exception("Save to sheets failed")

        logger.info("Pipeline completed successfully")
        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Job failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)