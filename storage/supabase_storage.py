"""
Supabase Storage Handler for uploading parquet files
Uses Supabase Storage API to store historical market data
UPDATED: Added token management methods for Upstox access token
"""

import io
import json
import pandas as pd
from typing import Dict, Optional, Tuple
from supabase import create_client, Client
from utils.logger import get_logger
from config.settings import SUPABASE_CONFIG, PARQUET_RETENTION

logger = get_logger(__name__)


class SupabaseStorage:
    """
    Handler for Supabase Storage operations
    Uploads parquet files and manages Upstox access tokens
    """
    
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase Storage Handler
        
        Args:
            url: Supabase project URL
            key: Supabase service role key
        """
        self.url = url
        self.key = key
        self.bucket_name = SUPABASE_CONFIG['bucket_name']
        self.token_path = 'credentials/upstox_token.json'
        self.client: Optional[Client] = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Supabase
        
        Returns:
            bool: True if authentication successful
        """
        try:
            logger.info("Authenticating with Supabase...")
            self.client = create_client(self.url, self.key)
            logger.info("✓ Successfully authenticated with Supabase")
            return True
            
        except Exception as e:
            logger.error(f"Supabase authentication error: {e}")
            return False
    
    def test_authentication(self) -> tuple[bool, str]:
        """
        Test authentication and access to Supabase Storage
        
        Returns:
            tuple: (success: bool, message: str)
        """
        logger.info("\n" + "=" * 60)
        logger.info("TESTING SUPABASE STORAGE AUTHENTICATION")
        logger.info("=" * 60)
        
        try:
            # Test 1: Authenticate
            logger.info("\nTest 1: Authenticating with Supabase...")
            if not self.authenticate():
                return False, "Failed to authenticate with Supabase"
            logger.info("✓ Authentication successful")
            
            # Test 2: Check if bucket exists
            logger.info("\nTest 2: Checking bucket existence...")
            try:
                buckets = self.client.storage.list_buckets()
                bucket_exists = any(b['name'] == self.bucket_name for b in buckets)
                
                if not bucket_exists:
                    logger.info(f"Bucket '{self.bucket_name}' does not exist. Creating...")
                    self.client.storage.create_bucket(
                        self.bucket_name,
                        options={"public": True}
                    )
                    logger.info(f"✓ Created bucket: {self.bucket_name}")
                else:
                    logger.info(f"✓ Bucket exists: {self.bucket_name}")
                    
            except Exception as e:
                # Bucket might already exist
                logger.info(f"Note: {e}")
                logger.info(f"Assuming bucket '{self.bucket_name}' exists")
            
            # Test 3: Test write permissions
            logger.info("\nTest 3: Testing write permissions...")
            try:
                test_content = b"Test file for Supabase Storage access verification"
                
                self.client.storage.from_(self.bucket_name).upload(
                    path="_test_write_access.txt",
                    file=test_content,
                    file_options={"content-type": "text/plain", "upsert": "true"}
                )
                logger.info("✓ Write permission confirmed")
                
                # Clean up test file
                logger.info("  Cleaning up test file...")
                self.client.storage.from_(self.bucket_name).remove(["_test_write_access.txt"])
                logger.info("  ✓ Test file removed")
                
            except Exception as e:
                logger.error(f"✗ Write permission test failed: {e}")
                return False, f"Write permission error: {e}"
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ ALL SUPABASE STORAGE TESTS PASSED")
            logger.info("=" * 60)
            logger.info(f"Bucket: {self.bucket_name} (PUBLIC)")
            logger.info(f"Storage URL: {self.url}/storage/v1/object/public/{self.bucket_name}/")
            logger.info("=" * 60)
            
            return True, "All tests passed"
            
        except Exception as e:
            logger.error(f"\n✗ Supabase Storage test failed: {e}")
            return False, f"Test error: {e}"
    
    # ==================== TOKEN MANAGEMENT METHODS ====================
    
    def upload_token(self, token_data: Dict) -> Tuple[bool, str]:
        """
        Upload Upstox access token to Supabase Storage
        
        Args:
            token_data: Dictionary containing token and user info
                Expected keys: access_token, user_info, timestamp
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self.client:
                if not self.authenticate():
                    return False, "Failed to authenticate with Supabase"
            
            logger.info(f"Uploading token to {self.token_path}...")
            
            # Convert token data to JSON bytes
            token_json = json.dumps(token_data, indent=2)
            token_bytes = token_json.encode('utf-8')
            
            # Upload to Supabase (upsert = overwrite if exists)
            self.client.storage.from_(self.bucket_name).upload(
                path=self.token_path,
                file=token_bytes,
                file_options={"content-type": "application/json", "upsert": "true"}
            )
            
            logger.info(f"✓ Token uploaded successfully to Supabase")
            logger.info(f"  Path: {self.bucket_name}/{self.token_path}")
            
            return True, "Token uploaded successfully"
            
        except Exception as e:
            error_msg = f"Failed to upload token: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
    
    def download_token(self) -> Tuple[bool, Optional[Dict], str]:
        """
        Download Upstox access token from Supabase Storage
        
        Returns:
            Tuple[bool, Optional[Dict], str]: (success, token_data, message)
        """
        try:
            if not self.client:
                if not self.authenticate():
                    return False, None, "Failed to authenticate with Supabase"
            
            logger.info(f"Downloading token from {self.token_path}...")
            
            # Download from Supabase
            response = self.client.storage.from_(self.bucket_name).download(self.token_path)
            
            if not response:
                return False, None, "Token file not found in Supabase"
            
            # Parse JSON
            token_data = json.loads(response.decode('utf-8'))
            
            logger.info("✓ Token downloaded successfully from Supabase")
            logger.info(f"  User: {token_data.get('user_info', {}).get('user_name', 'N/A')}")
            logger.info(f"  Timestamp: {token_data.get('timestamp', 'N/A')}")
            
            return True, token_data, "Token downloaded successfully"
            
        except Exception as e:
            error_msg = f"Failed to download token: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, None, error_msg
    
    def check_token_exists(self) -> Tuple[bool, str]:
        """
        Check if token file exists in Supabase Storage
        
        Returns:
            Tuple[bool, str]: (exists, message)
        """
        try:
            if not self.client:
                if not self.authenticate():
                    return False, "Failed to authenticate with Supabase"
            
            # Try to download token
            response = self.client.storage.from_(self.bucket_name).download(self.token_path)
            
            if response:
                logger.info(f"✓ Token exists at {self.token_path}")
                return True, "Token exists"
            else:
                logger.info(f"✗ Token does not exist at {self.token_path}")
                return False, "Token not found"
            
        except Exception as e:
            error_msg = f"Error checking token: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg
    
    def delete_token(self) -> Tuple[bool, str]:
        """
        Delete token file from Supabase Storage
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self.client:
                if not self.authenticate():
                    return False, "Failed to authenticate with Supabase"
            
            logger.info(f"Deleting token from {self.token_path}...")
            
            # Delete from Supabase
            self.client.storage.from_(self.bucket_name).remove([self.token_path])
            
            logger.info("✓ Token deleted successfully from Supabase")
            return True, "Token deleted successfully"
            
        except Exception as e:
            error_msg = f"Failed to delete token: {str(e)}"
            logger.error(f"✗ {error_msg}")
            return False, error_msg
    
    # ==================== PARQUET MANAGEMENT METHODS ====================
    
    def prepare_parquet_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Prepare dataframe for parquet file (keep last 200 candles per symbol)
        Also optimizes data types to reduce file size
        
        Args:
            df: DataFrame to prepare
            timeframe: Timeframe identifier
        
        Returns:
            pd.DataFrame: Prepared and optimized dataframe
        """
        retention = PARQUET_RETENTION.get(timeframe, 200)
        
        logger.info(f"Preparing {timeframe} data for parquet...")
        logger.info(f"  Retention: Latest {retention} candles per symbol")
        
        # Keep latest N candles per symbol
        df_prepared = df.sort_values(['trading_symbol', 'timestamp']).groupby('trading_symbol').tail(retention).reset_index(drop=True)
        df_prepared = df_prepared.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"  Rows after retention: {len(df_prepared)}")
        
        # Optimize data types to reduce file size
        original_size = (df_prepared.memory_usage(deep=True).sum() / 1024) / 1024  # KB
        logger.info(f"  Original memory size: {original_size:.2f} MB")
        
        df_prepared = self._optimize_datatypes(df_prepared)
        
        optimized_size = (df_prepared.memory_usage(deep=True).sum() / 1024) / 1024  # KB
        reduction = ((original_size - optimized_size) / original_size) * 100
        logger.info(f"  Optimized memory size: {optimized_size:.2f} MB")
        logger.info(f"  Size reduction: {reduction:.1f}%")
        
        return df_prepared
    
    def _optimize_datatypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize dataframe datatypes to reduce memory usage
        - Round float columns to 2 decimal places and convert to float32
        - Convert int64 to smaller int types based on value ranges
        - Convert string columns to category for repeated values
        
        Args:
            df: DataFrame to optimize
        
        Returns:
            pd.DataFrame: Optimized dataframe
        """
        df_optimized = df.copy()
        
        for col in df_optimized.columns:
            col_type = df_optimized[col].dtype
            
            # Optimize float columns
            if col_type == 'float64':
                # Round to 2 decimal places
                df_optimized[col] = df_optimized[col].round(2)
                
                # Convert to float32 (float16 is too limited for price data)
                # float32 provides sufficient precision for 2 decimals
                df_optimized[col] = df_optimized[col].astype('float32')
            
            # Optimize integer columns
            elif col_type == 'int64':
                col_min = df_optimized[col].min()
                col_max = df_optimized[col].max()
                
                # Choose smallest int type that fits the data
                if col_min >= -128 and col_max <= 127:
                    df_optimized[col] = df_optimized[col].astype('int8')
                elif col_min >= -32768 and col_max <= 32767:
                    df_optimized[col] = df_optimized[col].astype('int16')
                elif col_min >= -2147483648 and col_max <= 2147483647:
                    df_optimized[col] = df_optimized[col].astype('int32')
            
            # Optimize string/object columns
            elif col_type == 'object':
                # Convert to category if there are repeated values
                # (Categories are efficient for columns with limited unique values)
                num_unique = df_optimized[col].nunique()
                num_total = len(df_optimized[col])
                
                # If less than 50% unique values, use category
                if num_unique / num_total < 0.5:
                    df_optimized[col] = df_optimized[col].astype('category')
        
        return df_optimized
    
    def upload_parquet(self, df: pd.DataFrame, timeframe: str) -> bool:
        """
        Upload dataframe as parquet file to Supabase Storage (in-memory)
        
        Args:
            df: DataFrame to upload
            timeframe: Timeframe identifier
        
        Returns:
            bool: True if successful
        """
        try:
            filename = SUPABASE_CONFIG['file_names'].get(timeframe)
            if not filename:
                logger.error(f"No filename configured for timeframe: {timeframe}")
                return False
            
            logger.info(f"Uploading {filename} to Supabase Storage...")
            
            # Prepare data (apply retention)
            df_prepared = self.prepare_parquet_data(df, timeframe)
            
            # Create parquet file in memory
            buffer = io.BytesIO()
            df_prepared.to_parquet(buffer, engine='pyarrow', compression='zstd', compression_level=9, index=False)

            buffer.seek(0)
            
            file_size_kb = (len(buffer.getvalue()) / 1024) / 1024
            logger.info(f"  Parquet file size: {file_size_kb:.2f} MB")
            
            # Upload to Supabase Storage (upsert overwrites existing file)
            self.client.storage.from_(self.bucket_name).upload(
                path=filename,
                file=buffer.getvalue(),
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
            
            logger.info(f"✓ Successfully uploaded {filename}")
            
            # Get public URL
            public_url = f"{self.url}/storage/v1/object/public/{self.bucket_name}/{filename}"
            logger.info(f"  Public URL: {public_url}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error uploading parquet file: {e}")
            return False
    
    def upload_all_timeframes(self, data_dict: Dict[str, pd.DataFrame]) -> bool:
        """
        Upload all timeframes as parquet files to Supabase Storage
        
        Args:
            data_dict: Dictionary mapping timeframe to DataFrame
        
        Returns:
            bool: True if all uploads successful
        """
        if not self.client:
            logger.error("Not authenticated. Call authenticate() first.")
            return False
        
        logger.info("\n" + "=" * 60)
        logger.info("UPLOADING PARQUET FILES TO SUPABASE STORAGE")
        logger.info("=" * 60)
        logger.info(f"Bucket: {self.bucket_name} (PUBLIC)")
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
            logger.info(f"✓ Files are publicly accessible at:")
            logger.info(f"   {self.url}/storage/v1/object/public/{self.bucket_name}/")
        else:
            logger.error("\n✗ Some parquet files failed to upload")
        
        return all_success