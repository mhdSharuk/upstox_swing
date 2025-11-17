"""
Percentage Calculator - Optimized for speed
Calculates percentage differences between HL2 and Supertrend values
REFACTORED: Only performs calculations, no CSV loading or merging
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from utils.logger import get_logger

logger = get_logger(__name__)


class PercentageCalculator:
    """
    Calculate percentage differences between HL2 and Supertrend values
    Highly optimized with vectorized operations
    """
    
    def __init__(self):
        """Initialize Percentage Calculator"""
        pass
    
    def calculate_percentage_differences(
        self,
        df: pd.DataFrame,
        configs: List[dict]
    ) -> pd.DataFrame:
        """
        Calculate percentage differences between HL2 and Supertrend values
        OPTIMIZED: Fully vectorized, no loops
        
        Two calculations per config:
        1. pct_diff_avg3_ST_X: % diff between avg(last 3 HL2) and supertrend
        2. pct_diff_latest_ST_X: % diff between latest HL2 and supertrend
        
        Formula: ((HL2 - Supertrend) / HL2) * 100
        
        Args:
            df: DataFrame with HL2 and supertrend columns
            configs: List of supertrend configurations
        
        Returns:
            pd.DataFrame: DataFrame with percentage difference columns added
        """
        df = df.copy()
        
        # Pre-calculate average of last 3 HL2 values per symbol (vectorized)
        df['avg3_hl2'] = df.groupby('trading_symbol')['hl2'].transform(
            lambda x: x.rolling(window=3, min_periods=1).mean()
        )
        
        # Calculate percentage differences for each config (vectorized)
        for config in configs:
            name = config['name']
            supertrend_col = f'supertrend_{name}'
            
            if supertrend_col not in df.columns:
                logger.warning(f"Supertrend column '{supertrend_col}' not found, skipping")
                continue
            
            # Vectorized percentage calculations with safeguards
            # Use np.where to handle division by zero and NaN values efficiently
            
            # 1. Average of last 3 HL2 vs Supertrend
            df[f'pct_diff_avg3_{name}'] = np.where(
                (df['avg3_hl2'].notna()) & (df[supertrend_col].notna()) & (df['avg3_hl2'] != 0),
                ((df['avg3_hl2'] - df[supertrend_col]) / df['avg3_hl2']) * 100,
                np.nan
            )
            
            # 2. Latest HL2 vs Supertrend
            df[f'pct_diff_latest_{name}'] = np.where(
                (df['hl2'].notna()) & (df[supertrend_col].notna()) & (df['hl2'] != 0),
                ((df['hl2'] - df[supertrend_col]) / df['hl2']) * 100,
                np.nan
            )
            
            # Cap extreme values to prevent outliers (vectorized)
            # Values beyond ±1000% are likely data errors
            df[f'pct_diff_avg3_{name}'] = df[f'pct_diff_avg3_{name}'].clip(-1000.0, 1000.0)
            df[f'pct_diff_latest_{name}'] = df[f'pct_diff_latest_{name}'].clip(-1000.0, 1000.0)
        
        # Drop temporary column
        df = df.drop(columns=['avg3_hl2'])
        
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
        logger.info("Calculating percentage differences (vectorized)...")
        final_df = self.calculate_percentage_differences(combined_df, configs)
        
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