"""
Simple script to download instruments from Upstox and upload to Supabase
Uses the InstrumentMapper class from data_fetcher module
"""

import sys
import os
import json
import gzip
import requests
from io import BytesIO

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_fetcher.instrument_mapper import InstrumentMapper
from config.env_loader import SUPABASE_URL, SUPABASE_KEY
from auth.token_manager import TokenManager
from auth.upstox_auth import UpstoxAuthenticator
from utils.logger import get_logger

logger = get_logger(__name__)


def upload_to_supabase(instruments_data: list) -> bool:
    """
    Upload instruments data to Supabase storage as compressed JSON
    
    Args:
        instruments_data: List of instrument dictionaries
    
    Returns:
        bool: True if successful
    """
    try:
        bucket_name = "st-swing-bucket"
        file_path = "data/instruments_complete.json.gz"
        
        logger.info("\nPreparing to upload to Supabase...")
        logger.info(f"  Bucket: {bucket_name}")
        logger.info(f"  Path: {file_path}")
        
        # Convert to JSON and compress
        json_data = json.dumps(instruments_data)
        compressed_data = gzip.compress(json_data.encode('utf-8'))
        
        file_size_mb = len(compressed_data) / (1024 * 1024)
        logger.info(f"  Compressed size: {file_size_mb:.2f} MB")
        
        # Upload to Supabase using REST API
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{file_path}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/octet-stream"
        }
        
        # Try upsert (overwrite if exists)
        response = requests.put(
            upload_url,
            headers=headers,
            data=compressed_data,
            params={"upsert": "true"}
        )
        
        if response.status_code in [200, 201]:
            logger.info(f"✓ Successfully uploaded to Supabase")
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{file_path}"
            logger.info(f"  Public URL: {public_url}")
            return True
        else:
            logger.error(f"✗ Upload failed: {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error uploading to Supabase: {e}")
        return False


def main():
    """Main function to download and upload instruments"""
    
    logger.info("=" * 60)
    logger.info("INSTRUMENT UPLOAD SCRIPT")
    logger.info("=" * 60)
    
    logger.info("\nStep 1: Downloading instruments from Upstox...")
    mapper = InstrumentMapper(None)
    
    # Force download from Upstox directly (not from Supabase fallback)
    success, results = mapper._fetch_from_upstox(allowed_symbols=None)
    # print(F'Results : {results}')


    if not success or not results:
        logger.error("✗ Failed to download instruments from Upstox")
        return False
    
    logger.info(f"✓ Downloaded {len(results)} instruments")
    
    # Step 3: Upload to Supabase
    logger.info("\nStep 3: Uploading to Supabase storage...")
    success = upload_to_supabase(results)
    
    if not success:
        logger.error("✗ Upload failed")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ UPLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Instruments uploaded: {len(results)}")
    
    return True


main()