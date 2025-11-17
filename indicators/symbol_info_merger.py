"""
Symbol Info Merger
Loads symbol information from CSV and merges with calculated data
Handles sector, industry, and market cap information
"""

import pandas as pd
from typing import Dict, Optional
from config.settings import SYMBOL_INFO_CONFIG
from utils.logger import get_logger

logger = get_logger(__name__)


class SymbolInfoMerger:
    """
    Load symbol information from CSV and merge with trading data
    Loads CSV once and reuses for all timeframes (efficient)
    """
    
    def __init__(self, csv_url: Optional[str] = None):
        """
        Initialize Symbol Info Merger
        
        Args:
            csv_url: URL to symbol info CSV (uses config default if not provided)
        """
        self.csv_url = csv_url or SYMBOL_INFO_CONFIG['url']
        self.symbol_info_df: Optional[pd.DataFrame] = None
    
    def load_symbol_info(self) -> bool:
        """
        Load symbol info CSV file from Google Sheets URL
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            logger.info("=" * 60)
            logger.info("LOADING SYMBOL INFO CSV")
            logger.info("=" * 60)
            logger.info(f"URL: {self.csv_url}")
            
            # Load CSV from URL
            df = pd.read_csv(self.csv_url)
            
            # Select and rename columns
            df = df[['Symbol', 'Sector', 'Industry', 'MCap Cr']]
            
            # Clean market cap (remove commas and convert to float)
            df['MCap Cr'] = df['MCap Cr'].apply(lambda x: float(x.replace(',', '')) if isinstance(x, str) else x)
            
            # Normalize column names
            df.columns = [x.strip().lower() for x in df.columns]
            
            # Rename to standard column names
            df.rename(columns={
                'symbol': 'trading_symbol',
                'sector': 'sector',
                'industry': 'industry',
                'mcap cr': 'market_cap'
            }, inplace=True)
            
            # Validate required columns
            required_cols = SYMBOL_INFO_CONFIG['required_columns']
            missing_cols = set(required_cols) - set(df.columns)
            
            if missing_cols:
                logger.error(f"Missing required columns in CSV: {missing_cols}")
                return False
            
            self.symbol_info_df = df
            
            logger.info(f"✓ Loaded symbol info for {len(self.symbol_info_df)} symbols")
            logger.info(f"  Columns: {list(self.symbol_info_df.columns)}")
            logger.info(f"  Unique sectors: {self.symbol_info_df['sector'].nunique()}")
            logger.info(f"  Unique industries: {self.symbol_info_df['industry'].nunique()}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error loading symbol info CSV: {e}")
            return False
    
    def merge_with_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Merge trading data with symbol information
        
        Args:
            df: DataFrame with trading data
            timeframe: Timeframe identifier (for logging)
        
        Returns:
            pd.DataFrame: Merged DataFrame with sector, industry, market_cap columns
        """
        if self.symbol_info_df is None:
            logger.error("Symbol info not loaded. Call load_symbol_info() first.")
            return df
        
        logger.info("=" * 60)
        logger.info(f"MERGING SYMBOL INFO - {timeframe.upper()}")
        logger.info("=" * 60)
        
        initial_rows = len(df)
        
        # Merge on trading_symbol (left join to keep all trading data)
        df_merged = df.merge(
            self.symbol_info_df[['trading_symbol', 'sector', 'industry', 'market_cap']],
            on='trading_symbol',
            how='left'
        )
        
        # Check for symbols without info
        missing_info = df_merged[df_merged['sector'].isna()]['trading_symbol'].unique()
        
        logger.info(f"✓ Merged {initial_rows} rows with symbol info")
        logger.info(f"  Symbols with info: {len(df_merged) - len(missing_info)}")
        
        if len(missing_info) > 0:
            logger.warning(f"  ⚠ {len(missing_info)} symbols have no sector/industry info")
            logger.warning(f"    Sample: {list(missing_info[:5])}")
        
        logger.info("=" * 60)
        
        return df_merged
    
    def merge_all_timeframes(
        self,
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Merge symbol info with all timeframes
        Loads CSV once and reuses for efficiency
        
        Args:
            data_dict: Dictionary mapping timeframe to DataFrame
        
        Returns:
            Dict[str, pd.DataFrame]: Merged data for all timeframes
        """
        # Load symbol info once
        if not self.load_symbol_info():
            logger.error("Failed to load symbol info CSV. Cannot proceed with merge.")
            return data_dict  # Return original data without merge
        
        # Merge with each timeframe
        merged_data = {}
        
        for timeframe, df in data_dict.items():
            merged_df = self.merge_with_data(df, timeframe)
            merged_data[timeframe] = merged_df
        
        logger.info("\n✓ Symbol info merge complete for all timeframes\n")
        
        return merged_data
    
    def get_statistics(self, df: pd.DataFrame, timeframe: str) -> Dict:
        """
        Get statistics about symbol info coverage
        
        Args:
            df: Merged DataFrame
            timeframe: Timeframe identifier
        
        Returns:
            Dict: Statistics dictionary
        """
        stats = {
            'total_rows': len(df),
            'unique_symbols': df['trading_symbol'].nunique(),
            'symbols_with_sector': df['sector'].notna().sum(),
            'symbols_without_sector': df['sector'].isna().sum(),
            'unique_sectors': df['sector'].nunique() if 'sector' in df.columns else 0,
            'unique_industries': df['industry'].nunique() if 'industry' in df.columns else 0
        }
        
        logger.info(f"\n{timeframe.upper()} Symbol Info Statistics:")
        logger.info(f"  Total rows: {stats['total_rows']}")
        logger.info(f"  Unique symbols: {stats['unique_symbols']}")
        logger.info(f"  Symbols with sector info: {stats['symbols_with_sector']}")
        logger.info(f"  Symbols without sector info: {stats['symbols_without_sector']}")
        logger.info(f"  Unique sectors: {stats['unique_sectors']}")
        logger.info(f"  Unique industries: {stats['unique_industries']}")
        
        return stats