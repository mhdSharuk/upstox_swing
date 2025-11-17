"""
Flat Base Detector - Detect flat base patterns in supertrend values
Optimized with Numba for high performance
UPDATED: Progress logging shows percentages instead of every 10 symbols
"""

import pandas as pd
import numpy as np
from numba import njit
from typing import List
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from config.settings import FLAT_BASE_TOLERANCE, FLAT_BASE_MIN_COUNT
from utils.logger import get_logger
from utils.validators import DataValidator

logger = get_logger(__name__)


@njit(cache=True)
def _detect_flat_base_numba(supertrend_values: np.ndarray, tolerance: float) -> np.ndarray:
    """
    Numba-optimized flat base detection
    
    Flat Base Definition:
    - Consecutive candles where supertrend values remain within tolerance
    - Formula: abs(supertrend[i] - supertrend[i-1]) / supertrend[i-1] <= tolerance
    - Count starts at 2 for consecutive flat bases
    
    Args:
        supertrend_values: Array of supertrend values
        tolerance: Tolerance for flat base detection (e.g., 0.001 = 0.1%)
    
    Returns:
        np.ndarray: Flat base count for each position
    """
    n = len(supertrend_values)
    flat_base_count = np.zeros(n, dtype=np.int32)
    
    for i in range(1, n):
        current = supertrend_values[i]
        previous = supertrend_values[i - 1]
        
        # Skip if either value is NaN
        if np.isnan(current) or np.isnan(previous):
            flat_base_count[i] = 0
            continue
        
        # Skip if previous is zero (to avoid division by zero)
        if previous == 0:
            flat_base_count[i] = 0
            continue
        
        # Calculate percentage difference
        pct_diff = abs((current - previous) / previous)
        
        # Check if within tolerance
        if pct_diff <= tolerance:
            # Increment count from previous
            flat_base_count[i] = flat_base_count[i - 1] + 1
        else:
            # Reset count to 1 (current candle is a new base)
            flat_base_count[i] = 1
    
    return flat_base_count


class FlatBaseDetector:
    """
    Detect flat base periods in supertrend values
    Optimized with Numba for high-performance computation
    
    Flat Base Definition:
    - Consecutive candles where supertrend values remain within 0.1% tolerance
    - Formula: abs(supertrend[i] - supertrend[i-1]) / supertrend[i-1] <= 0.001
    - Count starts at 2 for consecutive flat bases
    """
    
    def __init__(self, tolerance: float = FLAT_BASE_TOLERANCE, n_jobs: int = None):
        """
        Initialize Flat Base Detector
        
        Args:
            tolerance: Tolerance for flat base detection (default: 0.001 = 0.1%)
            n_jobs: Number of parallel jobs (default: None = use all CPU cores)
        """
        self.tolerance = tolerance
        self.min_count = FLAT_BASE_MIN_COUNT
        self.n_jobs = n_jobs if n_jobs is not None else mp.cpu_count()
    
    def detect_flat_base(
        self,
        supertrend_series: pd.Series,
        config_name: str
    ) -> pd.Series:
        """
        Detect flat base periods in a supertrend series
        
        Args:
            supertrend_series: Series of supertrend values
            config_name: Configuration name for logging
        
        Returns:
            pd.Series: Flat base count for each row
        """
        # Convert to numpy array for Numba processing
        supertrend_np = supertrend_series.values
        
        # Calculate flat base counts using Numba-optimized function
        flat_base_count_np = _detect_flat_base_numba(supertrend_np, self.tolerance)
        
        # Convert back to pandas Series
        return pd.Series(flat_base_count_np, index=supertrend_series.index)
    
    def add_flat_base_counts(
        self,
        df: pd.DataFrame,
        supertrend_configs: List[str]
    ) -> pd.DataFrame:
        """
        Add flat base count columns for multiple supertrend configurations
        
        Args:
            df: DataFrame with supertrend calculations
            supertrend_configs: List of supertrend configuration names
        
        Returns:
            pd.DataFrame: DataFrame with flat base count columns added
        """
        df = df.copy()
        
        for config_name in supertrend_configs:
            supertrend_col = f'supertrend_{config_name}'
            flatbase_col = f'flatbase_count_{config_name}'
            
            if supertrend_col not in df.columns:
                logger.warning(f"Supertrend column '{supertrend_col}' not found, skipping")
                continue
            
            # Detect flat bases using Numba-optimized function
            flat_base_series = self.detect_flat_base(
                df[supertrend_col],
                config_name
            )
            
            # Add to dataframe
            df[flatbase_col] = flat_base_series
            
            # Validate
            is_valid, message = DataValidator.validate_flat_base_count(df, flatbase_col)
            if not is_valid:
                logger.warning(f"Flat base validation warning for {config_name}: {message}")
            
            # Log statistics
            non_zero = (flat_base_series > 1).sum()
            max_count = flat_base_series.max()
            logger.debug(
                f"{config_name}: {non_zero} flat base periods detected "
                f"(max consecutive: {max_count})"
            )
        
        return df
    
    @staticmethod
    def _process_symbol(symbol: str, df: pd.DataFrame, config_names: List[str], 
                        tolerance: float, min_count: int) -> tuple:
        """
        Process a single symbol (static method for multiprocessing)
        
        Args:
            symbol: Symbol name
            df: DataFrame for the symbol
            config_names: List of configuration names
            tolerance: Tolerance for flat base detection
            min_count: Minimum count threshold
        
        Returns:
            tuple: (symbol, processed_dataframe) or (symbol, None) if error
        """
        try:
            if df.empty:
                logger.warning(f"{symbol}: Empty dataframe, skipping")
                return (symbol, None)
            
            # Create a temporary detector instance for this process
            detector = FlatBaseDetector(tolerance=tolerance)
            detector.min_count = min_count
            
            df_with_fb = detector.add_flat_base_counts(df, config_names)
            return (symbol, df_with_fb)
        except Exception as e:
            logger.error(f"{symbol}: Error processing - {str(e)}")
            return (symbol, None)
    
    def calculate_flat_bases_for_symbols(
        self,
        df_by_symbol: dict,
        configs: list
    ) -> dict:
        """
        Calculate flat base counts for all symbols (parallel processing)
        
        Args:
            df_by_symbol: Dictionary mapping symbol to DataFrame
            configs: List of supertrend configuration dictionaries
        
        Returns:
            dict: Updated dictionary with flat base counts
        """
        logger.info(f"Calculating flat base counts for {len(df_by_symbol)} symbols...")
        logger.info(f"Using {self.n_jobs} parallel workers with Numba acceleration")
        
        config_names = [config['name'] for config in configs]
        updated_dfs = {}
        
        # Use ProcessPoolExecutor for parallel processing
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(
                    self._process_symbol,
                    symbol,
                    df,
                    config_names,
                    self.tolerance,
                    self.min_count
                ): symbol
                for symbol, df in df_by_symbol.items()
            }
            
            # Collect results as they complete
            completed = 0
            total = len(future_to_symbol)
            last_percentage = -1
            
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    result_symbol, df_with_fb = future.result()
                    if df_with_fb is not None:
                        updated_dfs[result_symbol] = df_with_fb
                    
                    completed += 1
                    
                    # Log every 10% or at completion
                    percentage = int((completed / total) * 100)
                    if percentage >= last_percentage + 10 or completed == total:
                        logger.info(f"Progress: {completed}/{total} ({percentage}%)")
                        last_percentage = percentage
                        
                except Exception as e:
                    logger.error(f"{symbol}: Exception during processing - {str(e)}")
        
        logger.info(f"✓ Flat base detection complete for {len(updated_dfs)} symbols")
        
        return updated_dfs
    
    def get_flat_base_statistics(
        self,
        df: pd.DataFrame,
        config_name: str
    ) -> dict:
        """
        Get statistics about flat bases for a configuration
        
        Args:
            df: DataFrame with flat base counts
            config_name: Configuration name
        
        Returns:
            dict: Statistics dictionary
        """
        flatbase_col = f'flatbase_count_{config_name}'
        
        if flatbase_col not in df.columns:
            return {}
        
        series = df[flatbase_col]
        
        stats = {
            'total_candles': len(series),
            'flat_base_periods': (series >= self.min_count).sum(),
            'max_consecutive': int(series.max()) if not series.empty else 0,
            'mean_count': float(series.mean()) if not series.empty else 0.0,
            'periods_above_5': (series >= 5).sum(),
            'periods_above_10': (series >= 10).sum()
        }
        
        return stats