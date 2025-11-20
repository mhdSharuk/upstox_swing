"""
Data validation utilities for Upstox Supertrend Project
FIXED VERSION: Better error handling for missing columns and dynamic validation
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class DataValidator:
    """
    Validate data integrity at various stages of processing
    """
    
    @staticmethod
    def validate_candle_data(df: pd.DataFrame, required_columns: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Validate OHLCV candle data
        
        Args:
            df: DataFrame with candle data
            required_columns: List of required columns (default: OHLCV columns)
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if required_columns is None:
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Check if DataFrame is empty
        if df is None:
            return False, "DataFrame is None"
        
        if df.empty:
            return False, "DataFrame is empty"
        
        # Check if DataFrame has any columns
        if len(df.columns) == 0:
            return False, "DataFrame has no columns"
        
        # Check for required columns
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            return False, f"Missing required columns: {missing_columns}"
        
        # Check for null values in critical columns - ONLY if columns exist
        price_columns = ['open', 'high', 'low', 'close']
        available_price_cols = [col for col in price_columns if col in df.columns]
        
        if not available_price_cols:
            return False, "No price columns (open/high/low/close) found in DataFrame"
        
        # Check for null values
        try:
            null_counts = df[available_price_cols].isnull().sum()
            if null_counts.any():
                return False, f"Null values found in price columns: {null_counts[null_counts > 0].to_dict()}"
        except Exception as e:
            return False, f"Error checking null values: {str(e)}"
        
        # Check for negative prices
        try:
            if (df[available_price_cols] < 0).any().any():
                return False, "Negative prices found in data"
        except Exception as e:
            return False, f"Error checking negative prices: {str(e)}"
        
        # Only check high/low if both columns exist
        if 'high' in df.columns and 'low' in df.columns:
            # Check high >= low
            invalid_hl = df[df['high'] < df['low']]
            if not invalid_hl.empty:
                return False, f"Found {len(invalid_hl)} rows where high < low"
        
        # Only check open/close range if all required columns exist
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            # Check open/close within high/low range
            invalid_range = df[
                (df['open'] > df['high']) | (df['open'] < df['low']) |
                (df['close'] > df['high']) | (df['close'] < df['low'])
            ]
            if not invalid_range.empty:
                return False, f"Found {len(invalid_range)} rows where open/close outside high/low range"
        
        return True, "Data validation passed"
    
    @staticmethod
    def validate_supertrend_calculation(
        df: pd.DataFrame,
        supertrend_col: str,
        direction_col: str,
        atr_period: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validate supertrend calculation results with dynamic thresholds
        
        Args:
            df: DataFrame with supertrend calculations
            supertrend_col: Name of supertrend column
            direction_col: Name of direction column
            atr_period: ATR period used (for calculating expected warmup)
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if df.empty:
            return False, "DataFrame is empty"
        
        # Check if columns exist
        if supertrend_col not in df.columns:
            return False, f"Supertrend column '{supertrend_col}' not found"
        if direction_col not in df.columns:
            return False, f"Direction column '{direction_col}' not found"
        
        # Check for null values
        null_count = df[supertrend_col].isnull().sum()
        total_rows = len(df)
        
        # Calculate expected warmup period dynamically
        if atr_period is not None:
            # Warmup period is roughly the ATR period plus a small buffer
            # Cap at 50% of data to handle small datasets with large ATR periods
            # (e.g., 50 rows with ATR=20 needs ~25 nulls, which is 50%)
            max_expected_nulls = min(atr_period + 5, int(total_rows * 0.5))
        else:
            # If ATR period not provided, use percentage-based validation
            # Allow up to 30% null at start for warmup
            max_expected_nulls = int(total_rows * 0.3)
        
        if null_count > max_expected_nulls:
            return False, f"Too many null values in supertrend: {null_count}/{total_rows} (expected max: {max_expected_nulls})"
        
        # Check that nulls are at the beginning (warmup period), not scattered
        if null_count > 0:
            non_null_indices = df[supertrend_col].notna()
            if non_null_indices.any():
                first_non_null_idx = non_null_indices.idxmax()
                # Check if there are nulls after the first non-null value
                nulls_after_start = df[supertrend_col].iloc[first_non_null_idx:].isnull().sum()
                if nulls_after_start > 0:
                    return False, f"Found {nulls_after_start} null values after data started (nulls should only be at beginning)"
        
        # Ensure we have sufficient non-null data
        non_null_count = total_rows - null_count
        min_required_data = max(10, int(total_rows * 0.5))  # At least 10 rows or 50% of data
        if non_null_count < min_required_data:
            return False, f"Insufficient non-null data: {non_null_count}/{total_rows} (need at least {min_required_data})"
        
        # Check direction values (should be 1 or -1)
        direction_values = df[direction_col].dropna()
        if not direction_values.empty:
            valid_directions = direction_values.isin([1, -1]).all()
            if not valid_directions:
                invalid_values = direction_values[~direction_values.isin([1, -1])].unique()
                return False, f"Direction values must be 1 or -1, found: {list(invalid_values)}"
        
        # Check for negative supertrend values
        st_values = df[supertrend_col].dropna()
        if not st_values.empty and (st_values < 0).any():
            negative_count = (st_values < 0).sum()
            return False, f"Found {negative_count} negative supertrend values"
        
        return True, "Supertrend validation passed"
    
    @staticmethod
    def validate_flat_base_count(
        df: pd.DataFrame,
        flatbase_col: str
    ) -> Tuple[bool, str]:
        """
        Validate flat base count calculations
        
        Args:
            df: DataFrame with flat base counts
            flatbase_col: Name of flat base count column
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if df.empty:
            return False, "DataFrame is empty"
        
        if flatbase_col not in df.columns:
            return False, f"Flat base column '{flatbase_col}' not found"
        
        # Check for negative counts
        fb_values = df[flatbase_col].dropna()
        if not fb_values.empty and (fb_values < 0).any():
            return False, "Negative flat base counts found"
        
        # Check for non-integer values
        if not fb_values.empty:
            if not (fb_values == fb_values.astype(int)).all():
                return False, "Flat base counts must be integers"
        
        return True, "Flat base validation passed"
    
    @staticmethod
    def validate_instrument_mapping(
        instruments: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Validate instrument mapping dictionary
        
        Args:
            instruments: Dictionary mapping trading_symbol to instrument_key
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not instruments:
            return False, "Instrument mapping is empty"
        
        # Check for empty keys or values
        for symbol, key in instruments.items():
            if not symbol or not isinstance(symbol, str):
                return False, f"Invalid trading symbol: {symbol}"
            if not key or not isinstance(key, str):
                return False, f"Invalid instrument key for {symbol}: {key}"
            if 'INE' not in key:
                return False, f"Instrument key should contain 'INE': {key}"
        
        logger.info(f"Validated {len(instruments)} instrument mappings")
        return True, "Instrument mapping validation passed"
    
    @staticmethod
    def validate_state_variables(
        state: Dict,
        required_keys: List[str]
    ) -> Tuple[bool, str]:
        """
        Validate state variables for incremental calculation
        
        Args:
            state: State dictionary
            required_keys: List of required keys
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        missing_keys = set(required_keys) - set(state.keys())
        if missing_keys:
            return False, f"Missing state keys: {missing_keys}"
        
        return True, "State variables validation passed"
    
    @staticmethod
    def check_data_continuity(df: pd.DataFrame, timeframe: str) -> List[str]:
        """
        Check for gaps in time series data
        
        Args:
            df: DataFrame with timestamp column
            timeframe: Timeframe identifier (e.g., '125min', 'daily')
        
        Returns:
            List[str]: List of warning messages (empty if no issues)
        """
        warnings = []
        
        if 'timestamp' not in df.columns:
            warnings.append("No timestamp column found")
            return warnings
        
        if len(df) < 2:
            return warnings
        
        # Sort by timestamp
        df_sorted = df.sort_values('timestamp').reset_index(drop=True)
        
        # Calculate time differences
        time_diffs = df_sorted['timestamp'].diff()
        
        # Expected differences based on timeframe
        if timeframe == '125min':
            # For 125-minute candles, expect differences of 125 minutes (allowing some tolerance)
            expected_diff = pd.Timedelta(minutes=125)
            tolerance = pd.Timedelta(minutes=30)  # Allow 30 min variance for market hours
        elif timeframe == 'daily':
            # For daily candles, expect 1-3 days (weekends/holidays)
            expected_diff = pd.Timedelta(days=1)
            tolerance = pd.Timedelta(days=5)  # Allow up to 5 days for long weekends
        else:
            return warnings
        
        # Check for unusual gaps
        unusual_gaps = time_diffs[(time_diffs > expected_diff + tolerance)].dropna()
        if not unusual_gaps.empty:
            warnings.append(
                f"Found {len(unusual_gaps)} unusual time gaps in {timeframe} data "
                f"(max: {unusual_gaps.max()})"
            )
        
        return warnings