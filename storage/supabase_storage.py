"""
Supabase Storage Handler for uploading parquet files
Uses Supabase Storage API to store historical market data
"""

import io
import pandas as pd
from typing import Dict, Optional
from supabase import create_client, Client
from utils.logger import get_logger
from config.settings import SUPABASE_CONFIG, PARQUET_RETENTION

logger = get_logger(__name__)


class SupabaseStorage:
    """
    Handler for Supabase Storage operations
    Uploads parquet files to Supabase Storage bucket
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
    
    def prepare_parquet_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Prepare dataframe for parquet file (keep last 200 candles per symbol)
        
        Args:
            df: DataFrame to prepare
            timeframe: Timeframe identifier
        
        Returns:
            pd.DataFrame: Prepared dataframe
        """
        retention = PARQUET_RETENTION.get(timeframe, 200)
        
        logger.info(f"Preparing {timeframe} data for parquet...")
        logger.info(f"  Retention: Latest {retention} candles per symbol")
        
        # Keep latest N candles per symbol
        df_prepared = df.sort_values(['trading_symbol', 'timestamp']).groupby('trading_symbol').tail(retention).reset_index(drop=True)
        df_prepared = df_prepared.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
        
        logger.info(f"  Rows after retention: {len(df_prepared)}")
        
        return df_prepared
    
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
            df_prepared.to_parquet(buffer, engine='pyarrow', compression='snappy', index=False)
            buffer.seek(0)
            
            file_size_kb = len(buffer.getvalue()) / 1024
            logger.info(f"  Parquet file size: {file_size_kb:.2f} KB")
            
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