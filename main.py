"""
Main Orchestration Script for Upstox Supertrend Project
UPDATED: Added signal generation steps 7 & 8
"""

import sys
import os
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    SUPERTREND_CONFIGS_125M,
    SUPERTREND_CONFIGS_60M,
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

setup_logging()
logger = get_logger(__name__)


class UpstoxSupertrendPipeline:
    
    def __init__(self):
        self.token_manager = TokenManager("credentials/upstox_token.json")
        self.access_token = None
        self.instruments_dict = {}
        self.historical_data = {}
        self.calculated_data = {}
        self.state_variables = {}
        self.with_percentages = {}
        self.final_data = {}
        self.signals_data = {}
        self.supabase_storage = None
    
    def step0_test_supabase_storage(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 0: TEST SUPABASE STORAGE ACCESS")
        logger.info("=" * 60)
        
        if not SUPABASE_URL or SUPABASE_URL == "your_supabase_url_here":
            logger.error("✗ Supabase URL not configured!")
            return False
        
        if not SUPABASE_KEY or SUPABASE_KEY == "your_supabase_key_here":
            logger.error("✗ Supabase Key not configured!")
            return False
        
        self.supabase_storage = SupabaseStorage(SUPABASE_URL, SUPABASE_KEY)
        
        success, message = self.supabase_storage.test_authentication()
        
        if not success:
            logger.error(f"✗ Supabase Storage test failed: {message}")
            return False
        
        logger.info("✓ Supabase Storage access verified!")
        return True
    
    def step1_authenticate(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: AUTHENTICATION")
        logger.info("=" * 60)
        
        if self.token_manager.load_token():
            if self.token_manager.validate_token():
                logger.info("✓ Token is valid")
                self.access_token = self.token_manager.access_token
                return True
        
        logger.info("Starting authentication flow...")
        authenticator = UpstoxAuthenticator(
            api_key=UPSTOX_API_KEY,
            api_secret=UPSTOX_API_SECRET,
            redirect_uri=UPSTOX_REDIRECT_URI,
            totp_secret=UPSTOX_TOTP_SECRET
        )
        
        token_data = authenticator.authenticate()
        
        if token_data:
            self.token_manager.save_token(token_data)
            self.access_token = token_data['access_token']
            logger.info("✓ Authentication successful")
            return True
        else:
            logger.error("✗ Authentication failed")
            return False
    
    def step2_fetch_instruments(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: FETCH INSTRUMENT KEYS")
        logger.info("=" * 60)
        
        symbol_merger = SymbolInfoMerger()
        
        if not symbol_merger.load_symbol_info():
            logger.warning("Could not load symbol info CSV. Proceeding without filtering.")
            allowed_symbols = None
        else:
            min_mcap = INSTRUMENT_FILTERS['min_market_cap']
            symbol_df = symbol_merger.symbol_info_df
            
            filtered_df = symbol_df[symbol_df['market_cap'] >= min_mcap]#.head(100)
            allowed_symbols = set(filtered_df['trading_symbol'].tolist())
            
            logger.info(f"✓ Symbol info loaded:")
            logger.info(f"  Total symbols in CSV: {len(symbol_df)}")
            logger.info(f"  Symbols with market cap >= {min_mcap} Cr: {len(allowed_symbols)}")
        
        mapper = InstrumentMapper(self.access_token)
        self.instruments_dict = mapper.create_instrument_mapping(allowed_symbols)
        
        if not self.instruments_dict:
            logger.error("✗ No instruments found")
            return False
        
        logger.info(f"✓ Found {len(self.instruments_dict)} instruments")
        return True
    
    def step3_fetch_historical_data(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: FETCH HISTORICAL DATA")
        logger.info("=" * 60)
        
        fetcher = HistoricalDataFetcher(self.access_token)
        timeframes = list(TIMEFRAME_CONFIG.keys())
        
        data_by_timeframe = fetcher.fetch_instruments_data(self.instruments_dict, timeframes)
        
        if not data_by_timeframe:
            logger.error("✗ Failed to fetch historical data")
            return False
        
        self.historical_data = fetcher.combine_instrument_data(data_by_timeframe)
        
        if not self.historical_data:
            logger.error("✗ Failed to combine historical data")
            return False
        
        for timeframe, df in self.historical_data.items():
            logger.info(f"  {timeframe}: {len(df)} rows, {df['trading_symbol'].nunique()} symbols")
        
        logger.info("✓ Historical data fetch complete")
        return True
    
    def step4_calculate_indicators(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: CALCULATE SUPERTREND INDICATORS")
        logger.info("=" * 60)
        
        calculator = SupertrendCalculator()
        
        timeframe_configs = {
            # '60min': SUPERTREND_CONFIGS_60M,
            '125min': SUPERTREND_CONFIGS_125M,
            # 'daily': SUPERTREND_CONFIGS_DAILY
        }
        
        self.calculated_data = {}
        self.state_variables = {}
        
        for timeframe, df in self.historical_data.items():
            configs = timeframe_configs.get(timeframe, [])
            
            if not configs:
                logger.warning(f"No configs found for {timeframe}")
                continue
            
            logger.info(f"Calculating {timeframe} indicators...")
            
            df_by_symbol = {symbol: group for symbol, group in df.groupby('trading_symbol')}
            
            calculated_dfs, states = calculator.calculate_with_state_preservation(
                df_by_symbol,
                configs,
                timeframe,
                use_parallel=True
            )
            
            combined_df = pd.concat(calculated_dfs.values(), ignore_index=True)
            self.calculated_data[timeframe] = combined_df
            self.state_variables[timeframe] = states
            
            logger.info(f"  ✓ {timeframe}: {len(combined_df)} rows calculated")
        
        logger.info("✓ Indicator calculation complete")
        return True
    
    def step5_calculate_flatbase_and_percentages(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: CALCULATE FLAT BASE & PERCENTAGES")
        logger.info("=" * 60)
        
        flat_detector = FlatBaseDetector()
        pct_calculator = PercentageCalculator()
        symbol_merger = SymbolInfoMerger()
        
        timeframe_configs = {
            # '60min': SUPERTREND_CONFIGS_60M,
            '125min': SUPERTREND_CONFIGS_125M,
            # 'daily': SUPERTREND_CONFIGS_DAILY
        }
        
        for timeframe, df in self.calculated_data.items():
            configs = timeframe_configs.get(timeframe, [])
            
            logger.info(f"Processing {timeframe}...")
            
            # Flat base detection
            df_by_symbol = {symbol: group for symbol, group in df.groupby('trading_symbol')}
            df_with_flat_dict = flat_detector.calculate_flat_bases_for_symbols(df_by_symbol, configs)
            df_with_flat = pd.concat(df_with_flat_dict.values(), ignore_index=True)
            
            # Percentage calculation
            df_by_symbol_pct = {symbol: group for symbol, group in df_with_flat.groupby('trading_symbol')}
            df_with_pct = pct_calculator.process_timeframe_data(df_by_symbol_pct, configs, timeframe)
            
            # Symbol info merge
            df_final = symbol_merger.merge_with_data(df_with_pct, timeframe)
            
            self.with_percentages[timeframe] = df_final
            
            logger.info(f"  ✓ {timeframe}: {len(df_final)} rows processed")
        
        self.final_data = self.with_percentages
        
        logger.info("✓ Flat base and percentage calculation complete")
        return True
    
    def step6_upload_to_supabase(self) -> bool:
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: UPLOAD TO SUPABASE STORAGE")
        logger.info("=" * 60)
        
        if not self.supabase_storage:
            logger.error("Supabase Storage not initialized")
            return False
        
        success = self.supabase_storage.upload_all_timeframes(self.final_data)
        
        if success:
            logger.info("✓ Parquet files uploaded to Supabase Storage successfully")
        else:
            logger.error("✗ Failed to upload parquet files to Supabase Storage")
        
        return success
    
    def run(self) -> bool:
        start_time = datetime.now()
        
        logger.info("\n" + "=" * 60)
        logger.info("UPSTOX SUPERTREND PIPELINE STARTED")
        logger.info("=" * 60)
        logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            if not self.step0_test_supabase_storage():
                logger.error("Pipeline failed at Step 0")
                return False
            
            if not self.step1_authenticate():
                logger.error("Pipeline failed at Step 1")
                return False
            
            if not self.step2_fetch_instruments():
                logger.error("Pipeline failed at Step 2")
                return False
            
            if not self.step3_fetch_historical_data():
                logger.error("Pipeline failed at Step 3")
                return False
            
            if not self.step4_calculate_indicators():
                logger.error("Pipeline failed at Step 4")
                return False
            
            if not self.step5_calculate_flatbase_and_percentages():
                logger.error("Pipeline failed at Step 5")
                return False
            
            if not self.step6_upload_to_supabase():
                logger.error("Pipeline failed at Step 6")
                return False
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Duration: {duration}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"\n\nPipeline failed with error: {e}", exc_info=True)
            return False


def main():
    pipeline = UpstoxSupertrendPipeline()
    success = pipeline.run()
    
    if success:
        logger.info("\n✓ All operations completed successfully")
        return 0
    else:
        logger.error("\n✗ Pipeline execution failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)