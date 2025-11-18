"""
Main Orchestration Script for Upstox Supertrend Project
Ties all components together to fetch data, calculate indicators, and save to Supabase Storage
UPDATED: Supabase Storage integration (Google Sheets/Drive removed)
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
    TIMEFRAME_CONFIG,
    INSTRUMENT_FILTERS,
    SUPABASE_CONFIG
)
from config.env_loader import (
    UPSTOX_API_KEY,
    UPSTOX_API_SECRET,
    UPSTOX_REDIRECT_URI,
    UPSTOX_TOTP_SECRET,
    SUPABASE_URL,
    SUPABASE_KEY
)

from auth.token_manager import TokenManager
from auth.upstox_auth import UpstoxAuthenticator
from data_fetcher.instrument_mapper import InstrumentMapper
from data_fetcher.historical_data import HistoricalDataFetcher
from indicators.supertrend_numba import SupertrendCalculator
from indicators.flat_base_numba import FlatBaseDetector
from indicators.percentage_calculator import PercentageCalculator
from indicators.symbol_info_merger import SymbolInfoMerger
from storage.supabase_storage import SupabaseStorage
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
        self.token_manager = TokenManager("credentials/upstox_token.json")
        self.access_token = None
        self.instruments_dict = {}
        self.historical_data = {}
        self.calculated_data = {}
        self.state_variables = {}
        self.with_percentages = {}
        self.final_data = {}
        self.supabase_storage = None
    
    def step0_test_supabase_storage(self) -> bool:
        """
        Step 0: Test Supabase Storage authentication and access
        This runs BEFORE everything else to ensure we can upload data
        
        Returns:
            bool: True if Supabase Storage is accessible
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 0: TEST SUPABASE STORAGE ACCESS")
        logger.info("=" * 60)
        
        # Check if Supabase credentials are configured
        if not SUPABASE_URL or SUPABASE_URL == "your_supabase_url_here":
            logger.error("✗ Supabase URL not configured!")
            logger.error("Please update SUPABASE_URL in .env or config/credentials.py")
            logger.error("\nHow to get your Supabase URL:")
            logger.error("1. Go to https://supabase.com/dashboard")
            logger.error("2. Select your project")
            logger.error("3. Go to Project Settings → API")
            logger.error("4. Copy the 'Project URL'")
            return False
        
        if not SUPABASE_KEY or SUPABASE_KEY == "your_supabase_key_here":
            logger.error("✗ Supabase Key not configured!")
            logger.error("Please update SUPABASE_KEY in .env or config/credentials.py")
            logger.error("\nHow to get your Supabase Key:")
            logger.error("1. Go to https://supabase.com/dashboard")
            logger.error("2. Select your project")
            logger.error("3. Go to Project Settings → API")
            logger.error("4. Copy the 'service_role' key (NOT the 'anon' key)")
            return False
        
        # Initialize Supabase Storage
        logger.info(f"Supabase URL: {SUPABASE_URL}")
        logger.info(f"Bucket: {SUPABASE_CONFIG['bucket_name']}")
        
        self.supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
        
        # Run comprehensive authentication test
        success, message = self.supabase_storage.test_authentication()
        
        if not success:
            logger.error("\n" + "=" * 60)
            logger.error("✗ SUPABASE STORAGE ACCESS FAILED")
            logger.error("=" * 60)
            logger.error("Cannot proceed with pipeline until Supabase Storage access is working.")
            logger.error("Please fix the issues above and try again.")
            logger.error("=" * 60)
            return False
        
        logger.info("✓ Supabase Storage access verified - ready to proceed!")
        
        return True
    
    def step1_authenticate(self) -> bool:
        """
        Step 1: Authenticate with Upstox
        Validate existing token or run login flow
        
        Returns:
            bool: True if authenticated successfully
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: AUTHENTICATE WITH UPSTOX")
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
        
        # If no valid token, get new one
        authenticator = UpstoxAuthenticator(
            UPSTOX_API_KEY,
            UPSTOX_API_SECRET,
            UPSTOX_REDIRECT_URI,
            UPSTOX_TOTP_SECRET
        )
        
        # Run the authentication flow
        if authenticator.authenticate():
            # Save the new token
            self.token_manager.save_token(
                authenticator.get_token(),
                authenticator.get_user_info()
            )
            self.access_token = authenticator.get_token()
            logger.info("✓ Authentication successful")
            return True
        
        logger.error("✗ Authentication failed")
        return False
    
    def step2_fetch_instruments(self) -> bool:
        """
        Step 2: Fetch instrument keys and create mapping (with market cap filtering)
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: FETCH INSTRUMENT KEYS")
        logger.info("=" * 60)
        
        # Load symbol info CSV to filter by market cap
        from indicators.symbol_info_merger import SymbolInfoMerger
        
        logger.info("Loading symbol info for market cap filtering...")
        symbol_merger = SymbolInfoMerger()
        
        if not symbol_merger.load_symbol_info():
            logger.error("✗ Failed to load symbol info CSV")
            logger.error("Cannot filter by market cap. Proceeding without filtering.")
            allowed_symbols = None
        else:
            # Filter symbols with market_cap >= min_market_cap
            min_mcap = INSTRUMENT_FILTERS['min_market_cap']
            symbol_df = symbol_merger.symbol_info_df
            
            # Filter by market cap
            filtered_df = symbol_df[symbol_df['market_cap'] >= min_mcap]
            allowed_symbols = set(filtered_df['trading_symbol'].tolist())
            
            logger.info(f"✓ Symbol info loaded:")
            logger.info(f"  Total symbols in CSV: {len(symbol_df)}")
            logger.info(f"  Symbols with market cap >= {min_mcap} Cr: {len(allowed_symbols)}")
            logger.info(f"  Filtered out: {len(symbol_df) - len(allowed_symbols)} symbols")
        
        # Fetch instruments with market cap filter
        mapper = InstrumentMapper(self.access_token)
        
        self.instruments_dict = mapper.create_instrument_mapping(allowed_symbols)
        
        if not self.instruments_dict:
            logger.error("✗ Failed to create instrument mapping")
            return False
        
        mapper.get_statistics()
        
        logger.info(f"Successfully mapped {len(self.instruments_dict)} instruments")
        
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
        
        logger.info("✓ Historical data fetch complete")
        
        return True
    
    def step4_calculate_supertrend(self) -> bool:
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
    
    def step5_detect_flat_base(self) -> bool:
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
    
    def step6_calculate_percentages(self) -> bool:
        """
        Step 6: Calculate percentage differences
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: CALCULATE PERCENTAGE DIFFERENCES")
        logger.info("=" * 60)
        
        # Initialize percentage calculator
        pct_calculator = PercentageCalculator()
        
        # Prepare configs dict
        configs_dict = {
            '125min': SUPERTREND_CONFIGS_125M,
            'daily': SUPERTREND_CONFIGS_DAILY
        }
        
        # Process all timeframes with percentage calculations
        self.with_percentages = pct_calculator.process_all_timeframes(
            self.calculated_data,
            configs_dict
        )
        
        if not self.with_percentages:
            logger.error("✗ Failed to calculate percentages")
            return False
        
        # Display statistics for each timeframe
        for timeframe, df in self.with_percentages.items():
            pct_calculator.get_statistics(df, timeframe)
        
        logger.info("✓ Percentage calculations complete")
        
        return True
    
    def step7_merge_symbol_info(self) -> bool:
        """
        Step 7: Merge with symbol info CSV
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 7: MERGE WITH SYMBOL INFO")
        logger.info("=" * 60)
        
        # Initialize symbol info merger
        symbol_merger = SymbolInfoMerger()
        
        # Merge all timeframes
        self.final_data = symbol_merger.merge_all_timeframes(self.with_percentages)
        
        if not self.final_data:
            logger.error("✗ Failed to merge symbol info")
            return False
        
        # Display statistics for each timeframe
        for timeframe, df in self.final_data.items():
            symbol_merger.get_statistics(df, timeframe)
        
        logger.info("✓ Symbol info merge complete")
        
        return True
    
    def step8_upload_to_supabase(self) -> bool:
        """
        Step 8: Upload parquet files to Supabase Storage
        
        Returns:
            bool: True if successful
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 8: UPLOAD TO SUPABASE STORAGE")
        logger.info("=" * 60)
        
        if not self.supabase_storage:
            logger.error("Supabase Storage not initialized!")
            return False
        
        # Upload all timeframes as parquet files
        success = self.supabase_storage.upload_all_timeframes(self.final_data)
        
        if success:
            logger.info("✓ Parquet files uploaded to Supabase Storage successfully")
        else:
            logger.error("✗ Failed to upload parquet files to Supabase Storage")
        
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
            # Step 0: Test Supabase Storage access FIRST
            if not self.step0_test_supabase_storage():
                logger.error("Pipeline failed at Step 0: Supabase Storage Access Test")
                logger.error("\n⚠️  CRITICAL: Fix Supabase Storage access before running the pipeline again!")
                return False
            
            # Step 1: Authenticate with Upstox
            if not self.step1_authenticate():
                logger.error("Pipeline failed at Step 1: Upstox Authentication")
                return False
            
            # Step 2: Fetch instruments
            if not self.step2_fetch_instruments():
                logger.error("Pipeline failed at Step 2: Fetch Instruments")
                return False
            
            # Step 3: Fetch historical data
            if not self.step3_fetch_historical_data():
                logger.error("Pipeline failed at Step 3: Fetch Historical Data")
                return False
            
            # Step 4: Calculate Supertrend
            if not self.step4_calculate_supertrend():
                logger.error("Pipeline failed at Step 4: Calculate Supertrend")
                return False
            
            # Step 5: Detect flat base patterns
            if not self.step5_detect_flat_base():
                logger.error("Pipeline failed at Step 5: Detect Flat Base")
                return False
            
            # Step 6: Calculate percentages
            if not self.step6_calculate_percentages():
                logger.error("Pipeline failed at Step 6: Calculate Percentages")
                return False
            
            # Step 7: Merge symbol info
            if not self.step7_merge_symbol_info():
                logger.error("Pipeline failed at Step 7: Merge Symbol Info")
                return False
            
            # Step 8: Upload to Supabase Storage
            if not self.step8_upload_to_supabase():
                logger.error("Pipeline failed at Step 8: Upload to Supabase Storage")
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
            logger.info(f"Supabase Storage: {SUPABASE_URL}/storage/v1/object/public/{SUPABASE_CONFIG['bucket_name']}/")
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