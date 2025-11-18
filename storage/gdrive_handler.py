"""
Google Drive Handler for uploading parquet files
Uses OAuth2 authentication to upload files as the user (not service account)
"""

import io
import os
import pandas as pd
from typing import Dict, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from utils.logger import get_logger
from config.settings import DRIVE_CONFIG, PARQUET_RETENTION

logger = get_logger(__name__)


class GoogleDriveHandler:
    """
    Handler for Google Drive operations using OAuth2
    Files are uploaded as the authenticated user (uses user's storage quota)
    """
    
    def __init__(self):
        """Initialize Google Drive Handler with OAuth2"""
        self.folder_name = DRIVE_CONFIG['folder_name']
        self.folder_id = DRIVE_CONFIG.get('folder_id')
        self.oauth_credentials_file = DRIVE_CONFIG['oauth_credentials_file']
        self.oauth_token_file = DRIVE_CONFIG['oauth_token_file']
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.service = None
        self.drive_available = True
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive using OAuth2
        First run: Opens browser for user authentication
        Subsequent runs: Uses saved token
        
        Returns:
            bool: True if authentication successful
        """
        try:
            logger.info("Authenticating with Google Drive (OAuth2)...")
            
            creds = None
            
            # Check if token file exists
            if os.path.exists(self.oauth_token_file):
                logger.info(f"Loading existing OAuth token from: {self.oauth_token_file}")
                creds = Credentials.from_authorized_user_file(self.oauth_token_file, self.scopes)
            
            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Token expired. Refreshing...")
                    creds.refresh(Request())
                    logger.info("✓ Token refreshed successfully")
                else:
                    # First time authentication - open browser
                    logger.info("\n" + "=" * 60)
                    logger.info("FIRST TIME OAUTH2 AUTHENTICATION")
                    logger.info("=" * 60)
                    logger.info("A browser window will open for you to authenticate.")
                    logger.info("Please log in with your Google account and click 'Allow'.")
                    logger.info("This is a ONE-TIME process.")
                    logger.info("=" * 60 + "\n")
                    
                    if not os.path.exists(self.oauth_credentials_file):
                        logger.error(f"✗ OAuth credentials file not found: {self.oauth_credentials_file}")
                        logger.error("\nPlease ensure you have:")
                        logger.error("1. Created OAuth2 credentials in Google Cloud Console")
                        logger.error("2. Downloaded the JSON file")
                        logger.error(f"3. Saved it as: {self.oauth_credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.oauth_credentials_file, 
                        self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("✓ Authentication successful!")
                
                # Save the credentials for next run
                logger.info(f"Saving OAuth token to: {self.oauth_token_file}")
                os.makedirs(os.path.dirname(self.oauth_token_file), exist_ok=True)
                with open(self.oauth_token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info("✓ Token saved for future use")
            else:
                logger.info("✓ Using existing valid OAuth token")
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=creds)
            
            logger.info("✓ Successfully authenticated with Google Drive (OAuth2)")
            return True
            
        except Exception as e:
            logger.error(f"Google Drive OAuth2 authentication error: {e}")
            return False
    
    def test_authentication(self) -> tuple[bool, str]:
        """
        Test authentication and access to Google Drive
        
        Returns:
            tuple: (success: bool, message: str)
        """
        logger.info("\n" + "=" * 60)
        logger.info("TESTING GOOGLE DRIVE AUTHENTICATION (OAuth2)")
        logger.info("=" * 60)
        
        try:
            # Test 1: Authenticate
            logger.info("\nTest 1: Authenticating with Google Drive (OAuth2)...")
            if not self.authenticate():
                return False, "Failed to authenticate with Google Drive"
            logger.info("✓ Authentication successful")
            
            # Test 2: Test API access
            logger.info("\nTest 2: Testing Drive API access...")
            try:
                results = self.service.files().list(
                    pageSize=1,
                    fields="files(id, name)"
                ).execute()
                logger.info("✓ Drive API access confirmed")
            except Exception as e:
                logger.error(f"✗ Drive API access failed: {e}")
                return False, f"Drive API access error: {e}"
            
            # Test 3: Test folder access
            logger.info("\nTest 3: Testing folder access...")
            folder_id = self.find_or_create_folder()
            if not folder_id:
                return False, "Failed to access/create folder"
            logger.info(f"✓ Folder accessible: {self.folder_name} (ID: {folder_id})")
            
            # Test 4: Test write permissions
            logger.info("\nTest 4: Testing write permissions...")
            try:
                test_content = b"Test file for Google Drive access verification"
                buffer = io.BytesIO(test_content)
                
                media = MediaIoBaseUpload(
                    buffer,
                    mimetype='text/plain',
                    resumable=True
                )
                
                file_metadata = {
                    'name': '_test_write_access.txt',
                    'parents': [self.folder_id]
                }
                
                test_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                
                test_file_id = test_file.get('id')
                logger.info("✓ Write permission confirmed")
                
                # Clean up test file
                logger.info("  Cleaning up test file...")
                self.service.files().delete(fileId=test_file_id).execute()
                logger.info("  ✓ Test file removed")
                
            except Exception as e:
                logger.error(f"✗ Write permission test failed: {e}")
                return False, f"Write permission error: {e}"
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ ALL GOOGLE DRIVE TESTS PASSED (OAuth2)")
            logger.info("=" * 60)
            logger.info("Files will be uploaded to YOUR Google Drive account")
            logger.info("Storage used: YOUR 15GB quota (not service account)")
            logger.info("=" * 60)
            
            return True, "All tests passed"
            
        except Exception as e:
            logger.error(f"\n✗ Google Drive test failed: {e}")
            return False, f"Test error: {e}"
    
    def find_or_create_folder(self) -> Optional[str]:
        """
        Find existing folder or create new one in user's Drive
        
        Returns:
            str: Folder ID or None if failed
        """
        try:
            # If folder_id is provided, verify access
            if self.folder_id:
                logger.info(f"Verifying access to folder (ID: {self.folder_id})...")
                try:
                    folder = self.service.files().get(
                        fileId=self.folder_id,
                        fields='id, name, capabilities'
                    ).execute()
                    
                    folder_name = folder.get('name', 'Unknown')
                    can_edit = folder.get('capabilities', {}).get('canEdit', False)
                    
                    if not can_edit:
                        logger.error(f"✗ No edit permissions on folder: {folder_name}")
                        return None
                    
                    logger.info(f"✓ Verified access to folder: {folder_name}")
                    return self.folder_id
                    
                except Exception as e:
                    logger.error(f"✗ Cannot access folder ID '{self.folder_id}': {e}")
                    logger.info("Will try to find/create folder by name...")
            
            # Search for folder by name
            query = f"name='{self.folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                self.folder_id = files[0]['id']
                logger.info(f"✓ Found existing folder: {self.folder_name} (ID: {self.folder_id})")
                return self.folder_id
            
            # Create new folder
            logger.info(f"Creating new folder: {self.folder_name}")
            file_metadata = {
                'name': self.folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            self.folder_id = folder.get('id')
            logger.info(f"✓ Created new folder: {self.folder_name} (ID: {self.folder_id})")
            return self.folder_id
            
        except Exception as e:
            logger.error(f"Error accessing/creating folder: {e}")
            return None
    
    def find_file_in_folder(self, filename: str) -> Optional[str]:
        """
        Find file by name in the folder
        
        Args:
            filename: Name of the file to find
        
        Returns:
            str: File ID or None if not found
        """
        try:
            query = f"name='{filename}' and '{self.folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding file: {e}")
            return None
    
    def prepare_parquet_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Prepare dataframe for parquet file (keep last 120 candles per symbol)
        
        Args:
            df: DataFrame to prepare
            timeframe: Timeframe identifier
        
        Returns:
            pd.DataFrame: Prepared dataframe
        """
        retention = PARQUET_RETENTION.get(timeframe, 120)
        
        logger.info(f"Preparing {timeframe} data for parquet...")
        logger.info(f"  Retention: Latest {retention} candles per symbol")
        
        # Keep latest 120 candles per symbol
        df_prepared = df.sort_values(['trading_symbol', 'timestamp']).groupby('trading_symbol').tail(retention).reset_index(drop=True)
        df_prepared = df_prepared.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"  Rows after retention: {len(df_prepared)}")
        
        return df_prepared
    
    def upload_parquet(self, df: pd.DataFrame, timeframe: str) -> bool:
        """
        Upload dataframe as parquet file to Google Drive (in-memory)
        
        Args:
            df: DataFrame to upload
            timeframe: Timeframe identifier
        
        Returns:
            bool: True if successful
        """
        try:
            filename = DRIVE_CONFIG['file_names'].get(timeframe)
            if not filename:
                logger.error(f"No filename configured for timeframe: {timeframe}")
                return False
            
            logger.info(f"Uploading {filename} to Google Drive...")
            
            # Prepare data (apply 120 candle retention)
            df_prepared = self.prepare_parquet_data(df, timeframe)
            
            # Create parquet file in memory
            buffer = io.BytesIO()
            df_prepared.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            
            file_size_kb = len(buffer.getvalue()) / 1024
            logger.info(f"  Parquet file size: {file_size_kb:.2f} KB")
            
            # Check if file exists
            existing_file_id = self.find_file_in_folder(filename)
            
            media = MediaIoBaseUpload(
                buffer,
                mimetype='application/octet-stream',
                resumable=True
            )
            
            if existing_file_id:
                # Update existing file
                logger.info(f"  Overwriting existing file (ID: {existing_file_id})...")
                self.service.files().update(
                    fileId=existing_file_id,
                    media_body=media
                ).execute()
                logger.info(f"✓ Successfully updated {filename}")
            else:
                # Create new file
                logger.info(f"  Creating new file...")
                file_metadata = {
                    'name': filename,
                    'parents': [self.folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"✓ Successfully created {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading parquet file: {e}")
            return False
    
    def upload_all_timeframes(self, data_dict: Dict[str, pd.DataFrame]) -> bool:
        """
        Upload all timeframes as parquet files to Google Drive
        
        Args:
            data_dict: Dictionary mapping timeframe to DataFrame
        
        Returns:
            bool: True if all uploads successful
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return False
        
        # Find or create folder
        if not self.find_or_create_folder():
            logger.error("Failed to find/create folder")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("UPLOADING PARQUET FILES TO GOOGLE DRIVE (OAuth2)")
        logger.info("=" * 60)
        logger.info(f"Folder: {self.folder_name}")
        logger.info(f"Timeframes to upload: {list(data_dict.keys())}")
        logger.info("=" * 60 + "\n")
        
        all_success = True
        
        for timeframe, df in data_dict.items():
            success = self.upload_parquet(df, timeframe)
            
            if not success:
                all_success = False
                logger.error(f"Failed to upload {timeframe} data")
        
        if all_success:
            logger.info("\n✓ All parquet files uploaded successfully!")
            logger.info("✓ Files are owned by YOUR Google account")
            logger.info("✓ Using YOUR storage quota (not service account)")
        else:
            logger.error("\n✗ Some parquet files failed to upload")
        
        return all_success