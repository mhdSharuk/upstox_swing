"""
Upstox Authenticator - Complete OAuth2 authentication flow
UPDATED: Continuous TOTP display with auto-refresh
"""

import requests
import pyotp
import webbrowser
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from typing import Optional, Dict
from utils.logger import get_logger

logger = get_logger(__name__)

# Global variable to store authorization code
auth_code_received = None


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler to capture the authorization code from Upstox redirect"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET request from Upstox redirect"""
        global auth_code_received
        
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        if 'code' in query_params:
            auth_code_received = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    .success {
                        color: #10b981;
                        font-size: 48px;
                        margin-bottom: 20px;
                    }
                    h1 { color: #1f2937; margin-bottom: 10px; }
                    p { color: #6b7280; font-size: 18px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✓</div>
                    <h1>Authentication Successful!</h1>
                    <p>Token saved. You can close this window now.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    .error { color: #ef4444; font-size: 48px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">✗</div>
                    <h1>Authentication Failed</h1>
                    <p>Please try again.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())


class UpstoxAuthenticator:
    """
    Handle complete Upstox OAuth2 authentication flow
    """
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str, totp_secret: str):
        """
        Initialize Upstox Authenticator
        
        Args:
            api_key: Upstox API key
            api_secret: Upstox API secret
            redirect_uri: OAuth redirect URI
            totp_secret: TOTP secret for 2FA
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.totp_secret = totp_secret
        self.access_token: Optional[str] = None
        self.user_info: Dict = {}
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
    
    def generate_totp(self) -> str:
        """
        Generate TOTP code for 2FA
        
        Returns:
            str: Current TOTP code
        """
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()
    
    def get_totp_time_remaining(self) -> int:
        """
        Get seconds remaining until current TOTP expires
        
        Returns:
            int: Seconds remaining
        """
        return 30 - (int(time.time()) % 30)
    
    def start_local_server(self, port: int = 8000) -> bool:
        """
        Start local HTTP server to capture authorization code
        
        Args:
            port: Port number for local server
        
        Returns:
            bool: True if server started successfully
        """
        global auth_code_received
        auth_code_received = None
        
        try:
            server_address = ('', port)
            self.server = HTTPServer(server_address, CallbackHandler)
            
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                daemon=True
            )
            self.server_thread.start()
            
            logger.info(f"Local server started on port {port}")
            return True
            
        except OSError as e:
            logger.error(f"Error starting local server: {e}")
            logger.error(f"Port {port} might be in use")
            return False
    
    def stop_local_server(self):
        """Stop the local HTTP server"""
        if self.server:
            self.server.shutdown()
            logger.info("Local server stopped")
    
    def get_authorization_url(self) -> str:
        """
        Generate OAuth authorization URL
        
        Returns:
            str: Authorization URL
        """
        base_url = "https://api.upstox.com/v2/login/authorization/dialog"
        params = {
            "response_type": "code",
            "client_id": self.api_key,
            "redirect_uri": self.redirect_uri,
            "state": f"upstox_auth_{int(time.time())}"
        }
        
        url = f"{base_url}?"
        url += "&".join([f"{key}={value}" for key, value in params.items()])
        return url
    
    def wait_for_authorization_code(self, timeout: int = 300) -> Optional[str]:
        """
        Wait for authorization code from callback
        UPDATED: Continuously displays and refreshes TOTP every 30 seconds
        
        Args:
            timeout: Maximum time to wait in seconds
        
        Returns:
            str: Authorization code or None if timeout
        """
        global auth_code_received
        
        logger.info(f"\nWaiting for authorization (timeout: {timeout}s)...")
        logger.info("=" * 60)
        
        start_time = time.time()
        last_totp = None
        totp_display_count = 0
        
        while auth_code_received is None:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logger.error("\n✗ Timeout waiting for authorization code")
                return None
            
            # Get current TOTP and time remaining
            current_totp = self.generate_totp()
            time_remaining = self.get_totp_time_remaining()
            
            # Display TOTP when it changes
            if current_totp != last_totp:
                totp_display_count += 1
                
                if totp_display_count > 1:
                    logger.info("\n" + "─" * 60)
                
                logger.info(f"📱 CURRENT TOTP CODE: {current_totp}")
                logger.info(f"⏱️  Code expires in: {time_remaining} seconds")
                logger.info(f"⏳ Waiting for authorization... ({int(timeout - elapsed)}s remaining)")
                
                last_totp = current_totp
            
            # Check every 0.5 seconds
            time.sleep(0.5)
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Authorization received!")
        logger.info("=" * 60)
        
        return auth_code_received
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """
        Exchange authorization code for access token
        
        Args:
            auth_code: Authorization code from OAuth flow
        
        Returns:
            bool: True if token obtained successfully
        """
        url = "https://api.upstox.com/v2/login/authorization/token"
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "code": auth_code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result.get("access_token")
            
            # Store user info
            self.user_info = {
                "user_id": result.get('user_id'),
                "user_name": result.get('user_name'),
                "email": result.get('email'),
                "exchanges": result.get('exchanges', []),
                "products": result.get('products', []),
            }
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ ACCESS TOKEN OBTAINED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"User ID: {self.user_info['user_id']}")
            logger.info(f"User Name: {self.user_info['user_name']}")
            logger.info(f"Email: {self.user_info['email']}")
            logger.info(f"Exchanges: {', '.join(self.user_info['exchanges'])}")
            logger.info("Token valid until 3:30 AM IST next day")
            logger.info("=" * 60)
            
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error getting access token: {e}")
            logger.error(f"Response: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Complete OAuth authentication flow
        UPDATED: Shows initial TOTP and then continuously refreshes during wait
        
        Returns:
            bool: True if authentication successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("UPSTOX AUTHENTICATION")
        logger.info("=" * 60)
        
        # Display current TOTP
        current_totp = self.generate_totp()
        time_remaining = self.get_totp_time_remaining()
        
        logger.info(f"\n📱 CURRENT TOTP CODE: {current_totp}")
        logger.info(f"⏱️  Code expires in: {time_remaining} seconds")
        logger.info("   (Code auto-refreshes every 30 seconds)\n")
        
        # Start local server
        port = int(urlparse(self.redirect_uri).port or 8000)
        if not self.start_local_server(port):
            return False
        
        # Generate and open authorization URL
        auth_url = self.get_authorization_url()
        logger.info("🌐 Opening Upstox login page in your browser...")
        logger.info(f"   If browser doesn't open, visit: {auth_url}\n")
        
        webbrowser.open(auth_url)
        
        logger.info("📋 INSTRUCTIONS:")
        logger.info("   1. Browser will open the Upstox login page")
        logger.info("   2. Enter your Upstox User ID and Password")
        logger.info("   3. When prompted for TOTP, use the code shown above")
        logger.info("   4. New TOTP codes will appear every 30 seconds below")
        logger.info("   5. Click 'Authorize' to allow access")
        logger.info("   6. The script will automatically capture and save the token!")
        
        # Wait for authorization code (with continuous TOTP display)
        auth_code = self.wait_for_authorization_code(timeout=300)
        
        # Stop the local server
        self.stop_local_server()
        
        if not auth_code:
            logger.error("\n✗ Failed to receive authorization code!")
            return False
        
        logger.info(f"\n✓ Authorization code received: {auth_code[:10]}...")
        
        # Exchange code for access token
        logger.info("\n🔄 Exchanging authorization code for access token...")
        return self.exchange_code_for_token(auth_code)
    
    def get_token(self) -> Optional[str]:
        """Get the access token"""
        return self.access_token
    
    def get_user_info(self) -> Dict:
        """Get user information"""
        return self.user_info