"""
Token Manager - Handle Upstox access token validation and management
"""

import json
import os
import requests
from datetime import datetime, time
from typing import Dict, Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class TokenManager:
    """
    Manage Upstox access tokens - validate, load, and refresh as needed
    """
    
    def __init__(self, token_file: str = "upstox_token.json"):
        """
        Initialize Token Manager
        
        Args:
            token_file: Path to the token JSON file
        """
        self.token_file = token_file
        self.access_token: Optional[str] = None
        self.user_info: Dict = {}
        self.token_timestamp: Optional[str] = None
    
    def load_token(self) -> bool:
        """
        Load access token from file
        
        Returns:
            bool: True if token loaded successfully, False otherwise
        """
        if not os.path.exists(self.token_file):
            logger.error(f"Token file '{self.token_file}' not found!")
            logger.info("Please run the login script first to authenticate")
            return False
        
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            self.access_token = token_data.get("access_token")
            self.user_info = token_data.get("user_info", {})
            self.token_timestamp = token_data.get("timestamp")
            
            if not self.access_token:
                logger.error("No access token found in file!")
                return False
            
            logger.info("Token loaded successfully")
            logger.info(f"User: {self.user_info.get('user_name')} ({self.user_info.get('user_id')})")
            logger.info(f"Token saved at: {self.token_timestamp}")
            
            return True
            
        except json.JSONDecodeError:
            logger.error("Error reading token file - file may be corrupted")
            return False
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            return False
    
    def validate_token(self) -> bool:
        """
        Validate if the current access token is still valid by making a test API call
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        if not self.access_token:
            logger.error("No access token available to validate")
            return False
        
        try:
            # Test API call to validate token
            url = "https://api.upstox.com/v2/user/profile"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            logger.info("Validating access token...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("✓ Token is valid and active")
                return True
            elif response.status_code == 401:
                logger.warning("✗ Token has expired or is invalid")
                return False
            else:
                logger.warning(f"Unexpected response during validation: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    def is_token_likely_expired(self) -> bool:
        """
        Check if token is likely expired based on Upstox expiry rules
        Upstox tokens expire at 3:30 AM IST
        
        Returns:
            bool: True if token is likely expired
        """
        if not self.token_timestamp:
            return True
        
        try:
            token_date = datetime.fromisoformat(self.token_timestamp)
            current_time = datetime.now()
            
            # Upstox tokens expire at 3:30 AM IST
            # If current time is after 3:30 AM and token was created yesterday or earlier
            expiry_time = time(3, 30)  # 3:30 AM
            
            if current_time.date() > token_date.date():
                # Token was created on a different day
                if current_time.time() > expiry_time:
                    logger.info("Token likely expired (created on different day, past 3:30 AM)")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Could not determine token expiry: {e}")
            return False
    
    def get_token(self) -> Optional[str]:
        """
        Get the current access token
        
        Returns:
            str: Access token or None if not available
        """
        return self.access_token
    
    def get_user_info(self) -> Dict:
        """
        Get user information associated with the token
        
        Returns:
            dict: User information dictionary
        """
        return self.user_info
    
    def ensure_valid_token(self) -> Tuple[bool, str]:
        """
        Ensure we have a valid access token
        First try to load and validate existing token
        If invalid, return status message for user to re-authenticate
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        # Try to load token
        if not self.load_token():
            return False, "Failed to load token. Please run login script."
        
        # Check if likely expired based on time
        if self.is_token_likely_expired():
            logger.warning("Token appears to be expired based on timestamp")
            # Still validate with API to be sure
        
        # Validate token with API
        if self.validate_token():
            return True, "Token is valid and ready to use"
        else:
            return False, "Token is invalid or expired. Please run login script to re-authenticate."
    
    def save_token(self, access_token: str, user_info: Dict) -> bool:
        """
        Save a new access token to file
        
        Args:
            access_token: The access token to save
            user_info: User information dictionary
        
        Returns:
            bool: True if saved successfully
        """
        token_data = {
            "access_token": access_token,
            "user_info": user_info,
            "timestamp": datetime.now().isoformat(),
            "expires_note": "Token expires at 3:30 AM IST next day"
        }
        
        try:
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=4)
            
            self.access_token = access_token
            self.user_info = user_info
            self.token_timestamp = token_data["timestamp"]
            
            logger.info(f"Token saved successfully to {self.token_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return False
