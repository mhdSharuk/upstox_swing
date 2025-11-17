import pandas as pd
from typing import Dict, List
from utils.logger import get_logger, ProgressLogger

logger = get_logger(__name__)

class PercentageCalculator:

    def __init__(self, symbol_info_csv: str = 'symbol_info.csv'):
        """
        Initialize Percentage Calculator
        
        Args:
            symbol_info_csv: Path to symbol info CSV file
        """
        self.symbol_info_csv = symbol_info_csv
        self.symbol_info_df = None
    
    def load_symbol_info(self) -> bool:
        """
        Load symbol info CSV file
        
        Returns:
            bool: True if loaded successfully
        """
        
        try:
            url = "https://docs.google.com/spreadsheets/d/1meVDXRT2eGBdmc1kRmtWiUd7iP-Ik1sxQHC_O4rz8K8/gviz/tq?tqx=out:csv&gid=1767398927"

            self.symbol_info_df = pd.read_csv(url)
            self.symbol_info_df = self.symbol_info_df[['Symbol', 'Sector', 'Industry', 'MCap Cr']]
            self.symbol_info_df['MCap Cr'] = self.symbol_info_df['MCap Cr'].apply(lambda x: float(x.replace(',', '')))
            self.symbol_info_df.columns = [x.strip().lower() for x in self.symbol_info_df.columns]
            self.symbol_info_df.rename(columns={
                'symbol' : 'trading_symbol',
                'sector': 'sector',
                'industry': 'industry',
                'mcap cr': 'market_cap'
            }, inplace=True)
            
            # Validate required columns
            required_cols = ['trading_symbol', 'sector', 'industry', 'market_cap']
            missing_cols = set(required_cols) - set(self.symbol_info_df.columns)
            
            if missing_cols:
                logger.error(f"Missing required columns in CSV: {missing_cols}")
                return False
            
            logger.info(f"✓ Loaded symbol info for {len(self.symbol_info_df)} symbols")
            logger.info(f"  Columns: {list(self.symbol_info_df.columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading symbol info CSV: {e}")
            return False
    
    def calculate_percentage_differences(
        self,
        df: pd.DataFrame,
        configs: List[dict]
    ) -> pd.DataFrame:
        """
        Calculate percentage differences between HL2 and Supertrend values
        
        Two calculations per config:
        1. pct_diff_avg3_ST_X: Percentage difference between avg(last 3 HL2) and supertrend
        2. pct_diff_latest_ST_X: Percentage difference between latest HL2 and supertrend
        
        Formula: ((HL2 - Supertrend) / HL2) * 100
        
        Handles edge cases:
        - Division by zero (HL2 = 0)
        - NaN values in HL2 or Supertrend
        - Replaces invalid results with None
        
        Args:
            df: DataFrame with HL2 and supertrend columns
            configs: List of supertrend configurations
        
        Returns:
            pd.DataFrame: DataFrame with percentage difference columns added
        """
        import numpy as np
        
        df = df.copy()
        
        # Calculate average of last 3 HL2 values per symbol
        df['avg3_hl2'] = df.groupby('trading_symbol')['hl2'].transform(
            lambda x: x.tail(3).mean()
        )
        
        # Get the latest HL2 value (which is already in the df as 'hl2')
        # No need to create a new column
        
        # Calculate percentage differences for each config
        for config in configs:
            name = config['name']
            supertrend_col = f'supertrend_{name}'
            
            if supertrend_col not in df.columns:
                logger.warning(f"Supertrend column '{supertrend_col}' not found, skipping")
                continue
            
            # Calculate percentage difference: ((HL2 - Supertrend) / HL2) * 100
            # With safeguards for division by zero and NaN values
            
            # 1. Average of last 3 HL2 vs Supertrend
            # Use np.where to handle division by zero
            df[f'pct_diff_avg3_{name}'] = np.where(
                (df['avg3_hl2'].notna()) & (df[supertrend_col].notna()) & (df['avg3_hl2'] != 0),
                ((df['avg3_hl2'] - df[supertrend_col]) / df['avg3_hl2']) * 100,
                None  # Return None for invalid cases
            )
            
            # 2. Latest HL2 vs Supertrend
            df[f'pct_diff_latest_{name}'] = np.where(
                (df['hl2'].notna()) & (df[supertrend_col].notna()) & (df['hl2'] != 0),
                ((df['hl2'] - df[supertrend_col]) / df['hl2']) * 100,
                None  # Return None for invalid cases
            )
            
            # Additional safeguard: Cap extreme values to prevent outliers
            # Values beyond ±1000% are likely data errors
            max_pct = 1000.0
            min_pct = -1000.0
            
            df[f'pct_diff_avg3_{name}'] = df[f'pct_diff_avg3_{name}'].clip(min_pct, max_pct)
            df[f'pct_diff_latest_{name}'] = df[f'pct_diff_latest_{name}'].clip(min_pct, max_pct)
        
        # Drop the temporary avg3_hl2 column
        df = df.drop(columns=['avg3_hl2'])
        
        # logger.info(f"✓ Calculated percentage differences for {len(configs)} configurations")
        
        return df
    
    def merge_with_symbol_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge calculated data with symbol info CSV
        
        Args:
            df: DataFrame with calculated data
        
        Returns:
            pd.DataFrame: Merged DataFrame with sector, industry, market_cap columns
        """
        if self.symbol_info_df is None:
            logger.error("Symbol info not loaded. Call load_symbol_info() first.")
            return df
        
        # Merge on trading_symbol
        df_merged = df.merge(
            self.symbol_info_df,
            on='trading_symbol',
            how='left'
        )
        
        # Check for symbols without info
        missing_info = df_merged[df_merged['sector'].isna()]['trading_symbol'].unique()
        
        if len(missing_info) > 0:
            logger.warning(f"⚠ {len(missing_info)} symbols have no sector/industry info")
            logger.warning(f"  Sample: {list(missing_info[:5])}")
        
        logger.info(f"✓ Merged with symbol info: {len(df_merged)} rows")
        
        return df_merged
    
    def process_timeframe_data(
        self,
        df_by_symbol: Dict[str, pd.DataFrame],
        configs: List[dict],
        timeframe: str
    ) -> pd.DataFrame:
        """
        Process all symbols for a timeframe:
        1. Calculate percentage differences
        2. Merge with symbol info
        
        Args:
            df_by_symbol: Dictionary mapping symbol to DataFrame
            configs: List of supertrend configurations
            timeframe: Timeframe identifier
        
        Returns:
            pd.DataFrame: Combined DataFrame with all calculations and symbol info
        """
        logger.info("=" * 60)
        logger.info(f"PROCESSING {timeframe.upper()} - PERCENTAGE CALCULATIONS & CSV MERGE")
        logger.info("=" * 60)
        
        all_dfs = []
        progress = ProgressLogger(len(df_by_symbol), f"Processing {timeframe} symbols", logger)
        
        for symbol, df in df_by_symbol.items():
            if df.empty:
                logger.warning(f"{symbol}: Empty dataframe, skipping")
                progress.update()
                continue
            
            # Calculate percentage differences
            df_with_pct = self.calculate_percentage_differences(df, configs)
            all_dfs.append(df_with_pct)
            
            progress.update()
        
        progress.complete(f"Processed {len(all_dfs)} symbols")
        
        # Combine all symbols
        if not all_dfs:
            logger.error("No data to process!")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"✓ Combined {len(combined_df)} rows from {len(all_dfs)} symbols")
        
        # Merge with symbol info
        final_df = self.merge_with_symbol_info(combined_df)
        
        logger.info("=" * 60)
        logger.info(f"✓ {timeframe.upper()} PROCESSING COMPLETE")
        logger.info("=" * 60)
        
        return final_df
    
    def process_all_timeframes(
        self,
        calculated_data: Dict[str, Dict[str, pd.DataFrame]],
        configs_dict: Dict[str, List[dict]]
    ) -> Dict[str, pd.DataFrame]:
        """
        Process all timeframes with percentage calculations and symbol info merge
        
        Args:
            calculated_data: Dictionary mapping timeframe to symbol DataFrames
            configs_dict: Dictionary mapping timeframe to configs
        
        Returns:
            Dict[str, pd.DataFrame]: Processed data for each timeframe
        """
        if not self.load_symbol_info():
            logger.error("Failed to load symbol info CSV. Cannot proceed.")
            return {}
        
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
        Get statistics about the processed data
        
        Args:
            df: Processed DataFrame
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
        
        logger.info(f"\n{timeframe.upper()} Statistics:")
        logger.info(f"  Total rows: {stats['total_rows']}")
        logger.info(f"  Unique symbols: {stats['unique_symbols']}")
        logger.info(f"  Symbols with sector info: {stats['symbols_with_sector']}")
        logger.info(f"  Symbols without sector info: {stats['symbols_without_sector']}")
        logger.info(f"  Unique sectors: {stats['unique_sectors']}")
        logger.info(f"  Unique industries: {stats['unique_industries']}")
        
        return stats