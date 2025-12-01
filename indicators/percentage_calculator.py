"""
Percentage Calculator - Optimized for speed
Calculates percentage differences between close and lowerband for shorter term supertrends
UPDATED: Modified to calculate (close - lowerband) / close * 100 for shorter term supertrends
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from utils.logger import get_logger

logger = get_logger(__name__)


class PercentageCalculator:
    """
    Calculate percentage differences between close and lowerband values
    Highly optimized with vectorized operations
    """
    
    # Define shorter term supertrends for each timeframe
    SHORTER_TERM_CONFIGS = {
        '60min': 'ST_60m_sma7',      # period=7 is shorter than period=35
        '125min': 'ST_125m_sma3',    # period=3 is shorter than period=15
        'daily': 'ST_daily_sma5'     # period=5 is shorter than period=20
    }
    
    def __init__(self):
        """Initialize Percentage Calculator"""
        pass
    
    def calculate_percentage_differences(
        self,
        df: pd.DataFrame,
        configs: List[dict],
        timeframe: str
    ) -> pd.DataFrame:
        """
        Calculate percentage difference between close and lowerband for shorter term supertrends
        OPTIMIZED: Fully vectorized, no loops
        
        Formula: ((close - lowerband) / close) * 100
        
        Only calculates for the shorter term supertrend of each timeframe:
        - 60min: ST_60m_sma7
        - 125min: ST_125m_sma3
        - Daily: ST_daily_sma5
        
        Args:
            df: DataFrame with close and lowerband columns
            configs: List of supertrend configurations
            timeframe: Timeframe identifier ('60min', '125min', 'daily')
        
        Returns:
            pd.DataFrame: DataFrame with percentage difference column added
        """
        df = df.copy()
        
        # Get the shorter term config name for this timeframe
        shorter_term_name = self.SHORTER_TERM_CONFIGS.get(timeframe)
        
        if not shorter_term_name:
            logger.warning(f"No shorter term config defined for timeframe: {timeframe}")
            return df
        
        # Find the matching config
        shorter_config = None
        for config in configs:
            if config['name'] == shorter_term_name:
                shorter_config = config
                break
        
        if not shorter_config:
            logger.warning(f"Shorter term config '{shorter_term_name}' not found in configs for {timeframe}")
            return df
        
        # Calculate percentage difference for shorter term supertrend only
        name = shorter_config['name']
        lowerband_col = f'lowerBand_{name}'
        
        if lowerband_col not in df.columns:
            logger.warning(f"Lowerband column '{lowerband_col}' not found, skipping")
            return df
        
        if 'close' not in df.columns:
            logger.warning(f"Close column not found, skipping")
            return df
        
        # Vectorized percentage calculation with safeguards
        # Formula: ((close - lowerband) / close) * 100
        # Use np.where to handle division by zero and NaN values efficiently
        df[f'pct_diff_close_lowerband_{name}'] = np.where(
            (df['close'].notna()) & (df[lowerband_col].notna()) & (df['close'] != 0),
            ((df['close'] - df[lowerband_col]) / df['close']) * 100,
            np.nan
        )
        
        # Cap extreme values to prevent outliers (vectorized)
        # Values beyond ±1000% are likely data errors
        df[f'pct_diff_close_lowerband_{name}'] = df[f'pct_diff_close_lowerband_{name}'].clip(-1000.0, 1000.0)
        
        logger.info(f"✓ Calculated pct_diff_close_lowerband_{name} for {timeframe}")
        
        return df
    
    def process_timeframe_data(
        self,
        df_by_symbol: Dict[str, pd.DataFrame],
        configs: List[dict],
        timeframe: str
    ) -> pd.DataFrame:
        """
        Process all symbols for a timeframe
        OPTIMIZED: Single concatenation, then vectorized operations on entire dataset
        
        Args:
            df_by_symbol: Dictionary mapping symbol to DataFrame
            configs: List of supertrend configurations
            timeframe: Timeframe identifier
        
        Returns:
            pd.DataFrame: Combined DataFrame with percentage calculations
        """
        logger.info("=" * 60)
        logger.info(f"CALCULATING PERCENTAGES - {timeframe.upper()}")
        logger.info("=" * 60)
        
        # Combine all symbols first (single concat operation)
        all_dfs = [df for df in df_by_symbol.values() if not df.empty]
        
        if not all_dfs:
            logger.error("No data to process!")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"✓ Combined {len(combined_df)} rows from {len(all_dfs)} symbols")
        
        # Calculate percentage differences (vectorized on entire dataset)
        logger.info(f"Calculating close-lowerband percentage difference for shorter term supertrend...")
        final_df = self.calculate_percentage_differences(combined_df, configs, timeframe)
        
        logger.info("=" * 60)
        logger.info(f"✓ {timeframe.upper()} PERCENTAGE CALCULATIONS COMPLETE")
        logger.info("=" * 60)
        
        return final_df
    
    def process_all_timeframes(
        self,
        calculated_data: Dict[str, Dict[str, pd.DataFrame]],
        configs_dict: Dict[str, List[dict]]
    ) -> Dict[str, pd.DataFrame]:
        """
        Process all timeframes with percentage calculations
        
        Args:
            calculated_data: Dictionary mapping timeframe to symbol DataFrames
            configs_dict: Dictionary mapping timeframe to configs
        
        Returns:
            Dict[str, pd.DataFrame]: Processed data for each timeframe
        """
        processed_data = {}
        
        for timeframe, df_by_symbol in calculated_data.items():
            configs = configs_dict.get(timeframe, [])
            
            if not configs:
                logger.warning(f"No configs found for {timeframe}, skipping")
                continue
            
            processed_df = self.process_timeframe_data(
                df_by_symbol,
                configs,
                timeframe
            )
            
            if not processed_df.empty:
                processed_data[timeframe] = processed_df
        
        return processed_data
    
    def get_statistics(self, df: pd.DataFrame, timeframe: str) -> Dict:
        """
        Get statistics about the calculated percentages
        
        Args:
            df: DataFrame with percentage calculations
            timeframe: Timeframe identifier
        
        Returns:
            Dict: Statistics dictionary
        """
        stats = {
            'total_rows': len(df),
            'unique_symbols': df['trading_symbol'].nunique(),
        }
        
        # Find percentage columns
        pct_cols = [col for col in df.columns if col.startswith('pct_diff_')]
        
        if pct_cols:
            stats['percentage_columns'] = len(pct_cols)
            stats['null_percentages'] = df[pct_cols].isnull().sum().to_dict()
        
        logger.info(f"\n{timeframe.upper()} Percentage Calculation Statistics:")
        logger.info(f"  Total rows: {stats['total_rows']}")
        logger.info(f"  Unique symbols: {stats['unique_symbols']}")
        logger.info(f"  Percentage columns added: {stats.get('percentage_columns', 0)}")
        
        return stats