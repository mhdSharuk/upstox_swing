"""
Main Orchestration Script for Upstox Supertrend Project
Ties all components together to fetch data, calculate indicators, and save to Google Sheets
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all necessary modules
from config.settings import (
    SUPERTREND_CONFIGS_125M,
    SUPERTREND_CONFIGS_DAILY,
    TIMEFRAME_CONFIG
)
from config.credentials import (
    UPSTOX_API_KEY,
    UPSTOX_API_SECRET,
    UPSTOX_REDIRECT_URI,
    UPSTOX_TOTP_SECRET,
    GOOGLE_SHEET_ID,
    SERVICE_ACCOUNT_FILE
)

from auth.token_manager import TokenManager
from auth.upstox_auth import UpstoxAuthenticator
from data_fetcher.instrument_mapper import InstrumentMapper
from data_fetcher.historical_data import HistoricalDataFetcher
from indicators.supertrend import SupertrendCalculator
from indicators.flat_base import FlatBaseDetector
from storage.sheets_writer import GoogleSheetsWriter
from utils.logger import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


class UpstoxSupertrendPipeline:
    """
    Main pipeline to orchestrate the entire process
    """
    
    def __init__(self):
        """Initialize the pipeline"""
        self.token_manager = TokenManager()
        self.access_token = None
        self.instruments_dict = {}
        self.historical_data = {}
        self.calculated_data = {}
        self.state_variables = {}
        self.sheets_writer = None
    
    def step0_test_google_sheets(self) -> bool:
        """
        Step 0: Test Google Sheets authentication and access
        This runs BEFORE everything else to ensure we can write data
        
        Returns:
            bool: True if Google Sheets is accessible
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 0: TEST GOOGLE SHEETS ACCESS")
        logger.info("=" * 60)
        
        # Check if Google Sheet ID is configured
        if GOOGLE_SHEET_ID == "your_google_sheet_id_here":
            logger.error("❌ Google Sheet ID not configured!")
            logger.error("Please update GOOGLE_SHEET_ID in config/credentials.py")
            logger.error("\nHow to get your Google Sheet ID:")
            logger.error("1. Open your Google Sheet")
            logger.error("2. Look at the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit")
            logger.error("3. Copy the YOUR_SHEET_ID part")
            return False
        
        # Check if service account file is configured
        if SERVICE_ACCOUNT_FILE == "path/to/service_account.json":
            logger.error("❌ Service account file path not configured!")
            logger.error("Please update SERVICE_ACCOUNT_FILE in config/credentials.py")
            logger.error("\nHow to get a service account:")
            logger.error("1. Go to Google Cloud Console")
            logger.error("2. Create a project or select existing one")
            logger.error("3. Enable Google Sheets API and Google Drive API")
            logger.error("4. Create a service account")
            logger.error("5. Download the JSON key file")
            return False
        
        # Initialize Google Sheets Writer
        logger.info(f"Sheet ID: {GOOGLE_SHEET_ID}")
        logger.info(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
        
        self.sheets_writer = GoogleSheetsWriter(GOOGLE_SHEET_ID, SERVICE_ACCOUNT_FILE)
        
        # Run comprehensive authentication test
        success, message = self.sheets_writer.test_authentication()
        
        if not success:
            logger.error("\n" + "=" * 60)
            logger.error("❌ GOOGLE SHEETS ACCESS FAILED")
            logger.error("=" * 60)
            logger.error("Cannot proceed with pipeline until Google Sheets access is working.")
            logger.error("Please fix the issues above and try again.")
            logger.error("=" * 60)
            return False
        
        logger.info("✓ Google Sheets access verified - ready to proceed!")
        return True
    
    def step1_authenticate(self) -> bool:
        """
        Step 1: Authenticate with Upstox
        Validate existing token or run login flow
        
        Returns:
            bool: True if authenticated successfully
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: AUTHENTICATION")
        logger.info("=" * 60)
        
        # Try to use existing token
        is_valid, message = self.token_manager.ensure_valid_token()
        
        if is_valid:
            self.access_token = self.token_manager.get_token()
            logger.info("✓ Using existing valid token")
            return True
        
        # Token is invalid or expired, need to re-authenticate
        logger.warning(message)
        logger.info("\nStarting authentication flow...")
        
        authenticator = UpstoxAuthenticator(
            UPSTOX_API_KEY,
            UPSTOX_API_SECRET,
            UPSTOX_REDIRECT_URI,
            UPSTOX_TOTP_SECRET
        )
        
        if authenticator.authenticate():
            # Save the new token
            self.token_manager.save_token(
                authenticator.get_token(),
                authenticator.get_user_info()
            )
            self.access_token = authenticator.get_token()
            logger.info("✓ Authentication successful")
            return True
        else:
            logger.error("✗ Authentication failed")
            return False
    
    def step2_fetch_instruments(self) -> bool:
        """
        Step 2: Fetch instrument keys and create mapping
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: FETCH INSTRUMENT KEYS")
        logger.info("=" * 60)
        
        mapper = InstrumentMapper()
        
        # Fetch instruments
        if not mapper.fetch_instruments():
            logger.error("✗ Failed to fetch instruments")
            return False
        
        # Create mapping
        self.instruments_dict = mapper.create_mapping()
        
        if not self.instruments_dict:
            logger.error("✗ Failed to create instrument mapping")
            return False
        
        # Display statistics
        mapper.get_statistics()
        
        # Optionally save to CSV for reference
        mapper.save_mapping_to_csv('instrument_mapping.csv')
        
        logger.info(f"✓ Successfully mapped {len(self.instruments_dict)} instruments")
        
        return True
    
    def step3_fetch_historical_data(self) -> bool:
        """
        Step 3: Fetch historical candle data for all instruments
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: FETCH HISTORICAL DATA")
        logger.info("=" * 60)
        
        fetcher = HistoricalDataFetcher(self.access_token)
        
        # Fetch data for both timeframes
        timeframes = ['125min', 'daily']
        
        self.historical_data = fetcher.fetch_instruments_data(
            self.instruments_dict,
            timeframes
        )
        
        if not self.historical_data:
            logger.error("✗ Failed to fetch historical data")
            return False
        
        logger.info(f"✓ Successfully fetched data for {len(timeframes)} timeframes")
        
        return True
    
    def step4_calculate_supertrends(self) -> bool:
        """
        Step 4: Calculate supertrend indicators for all timeframes
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: CALCULATE SUPERTREND INDICATORS")
        logger.info("=" * 60)
        
        st_calculator = SupertrendCalculator()
        
        # Process 125min timeframe
        if '125min' in self.historical_data:
            logger.info("\nCalculating 125-minute supertrends...")
            calculated_125m, states_125m = st_calculator.calculate_with_state_preservation(
                self.historical_data['125min'],
                SUPERTREND_CONFIGS_125M,
                '125min'
            )
            self.calculated_data['125min'] = calculated_125m
            self.state_variables['125min'] = states_125m
        
        # Process daily timeframe
        if 'daily' in self.historical_data:
            logger.info("\nCalculating daily supertrends...")
            calculated_daily, states_daily = st_calculator.calculate_with_state_preservation(
                self.historical_data['daily'],
                SUPERTREND_CONFIGS_DAILY,
                'daily'
            )
            self.calculated_data['daily'] = calculated_daily
            self.state_variables['daily'] = states_daily
        
        logger.info("✓ Supertrend calculations complete")
        
        return True
    
    def step5_detect_flat_bases(self) -> bool:
        """
        Step 5: Detect flat base patterns in supertrend values
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: DETECT FLAT BASE PATTERNS")
        logger.info("=" * 60)
        
        fb_detector = FlatBaseDetector()
        
        # Process 125min timeframe
        if '125min' in self.calculated_data:
            logger.info("\nDetecting flat bases in 125-minute data...")
            self.calculated_data['125min'] = fb_detector.calculate_flat_bases_for_symbols(
                self.calculated_data['125min'],
                SUPERTREND_CONFIGS_125M
            )
        
        # Process daily timeframe
        if 'daily' in self.calculated_data:
            logger.info("\nDetecting flat bases in daily data...")
            self.calculated_data['daily'] = fb_detector.calculate_flat_bases_for_symbols(
                self.calculated_data['daily'],
                SUPERTREND_CONFIGS_DAILY
            )
        
        logger.info("✓ Flat base detection complete")
        
        return True
    
    def step6_save_to_google_sheets(self) -> bool:
        """
        Step 6: Save calculated data to Google Sheets
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: SAVE TO GOOGLE SHEETS")
        logger.info("=" * 60)
        
        if not self.sheets_writer:
            logger.error("Google Sheets writer not initialized!")
            return False
        
        # The writer is already authenticated from step 0, but we'll verify again
        if not self.sheets_writer.client or not self.sheets_writer.spreadsheet:
            logger.info("Re-authenticating with Google Sheets...")
            if not self.sheets_writer.authenticate():
                logger.error("✗ Failed to authenticate with Google Sheets")
                return False
        
        # Combine data by symbol for each timeframe
        combined_data = {}
        
        for timeframe, symbol_dfs in self.calculated_data.items():
            if symbol_dfs:
                import pandas as pd
                # Concatenate all symbol DataFrames
                combined_df = pd.concat(symbol_dfs.values(), ignore_index=True)
                combined_data[timeframe] = combined_df
        
        # Prepare configs dict
        configs_dict = {
            '125min': SUPERTREND_CONFIGS_125M,
            'daily': SUPERTREND_CONFIGS_DAILY
        }
        
        # Write to Google Sheets
        success = self.sheets_writer.write_all_data(combined_data, configs_dict)
        
        if success:
            logger.info("✓ Data saved to Google Sheets successfully")
        else:
            logger.error("✗ Failed to save data to Google Sheets")
        
        return success
    
    def run(self) -> bool:
        """
        Run the complete pipeline
        
        Returns:
            bool: True if all steps successful
        """
        start_time = datetime.now()
        
        logger.info("\n" + "=" * 60)
        logger.info("UPSTOX SUPERTREND PIPELINE STARTED")
        logger.info("=" * 60)
        logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            # Step 0: Test Google Sheets access FIRST (before wasting time on data processing)
            if not self.step0_test_google_sheets():
                logger.error("Pipeline failed at Step 0: Google Sheets Access Test")
                logger.error("\n⚠️  CRITICAL: Fix Google Sheets access before running the pipeline again!")
                return False
            
            # Step 1: Authenticate
            if not self.step1_authenticate():
                logger.error("Pipeline failed at Step 1: Authentication")
                return False
            
            # Step 2: Fetch instruments
            if not self.step2_fetch_instruments():
                logger.error("Pipeline failed at Step 2: Fetch Instruments")
                return False
            
            # Step 3: Fetch historical data
            if not self.step3_fetch_historical_data():
                logger.error("Pipeline failed at Step 3: Fetch Historical Data")
                return False
            
            # Step 4: Calculate supertrends
            if not self.step4_calculate_supertrends():
                logger.error("Pipeline failed at Step 4: Calculate Supertrends")
                return False
            
            # Step 5: Detect flat bases
            if not self.step5_detect_flat_bases():
                logger.error("Pipeline failed at Step 5: Detect Flat Bases")
                return False
            
            # Step 6: Save to Google Sheets
            if not self.step6_save_to_google_sheets():
                logger.error("Pipeline failed at Step 6: Save to Google Sheets")
                return False
            
            # Success!
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Total duration: {duration}")
            logger.info(f"Instruments processed: {len(self.instruments_dict)}")
            logger.info(f"Data saved to: https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}")
            logger.info("=" * 60)
            
            return True
            
        except KeyboardInterrupt:
            logger.warning("\n\nPipeline interrupted by user")
            return False
        except Exception as e:
            logger.error(f"\n\nPipeline failed with error: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    pipeline = UpstoxSupertrendPipeline()
    success = pipeline.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()