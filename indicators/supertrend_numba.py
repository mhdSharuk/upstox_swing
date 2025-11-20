"""
Supertrend Calculator - 100% Pine Script Match with Numba Optimization
Optimized with Numba for high performance
Matches the exact logic from Pine Script normal_supertrend()
"""

import pandas as pd
import numpy as np
from numba import njit
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from .atr_numba import ATRCalculator
from utils.logger import get_logger, ProgressLogger
from utils.validators import DataValidator

logger = get_logger(__name__)


@njit(cache=True)
def _calculate_supertrend_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    hl2: np.ndarray,
    atr: np.ndarray,
    source: np.ndarray,
    atr_multiplier: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Numba-optimized supertrend calculation matching Pine Script exactly
    
    Pine Script Reference - See supertrend.py for full Pine Script code
    
    Args:
        high: High prices array
        low: Low prices array
        close: Close prices array
        hl2: HL2 values array
        atr: ATR values array
        source: Source values (HL2 or SMA of HL2)
        atr_multiplier: Multiplier for ATR bands
    
    Returns:
        Tuple: (supertrend, direction, upperBand, lowerBand) arrays
    """
    n = len(high)
    upperBand = np.empty(n, dtype=np.float64)
    lowerBand = np.empty(n, dtype=np.float64)
    supertrend = np.empty(n, dtype=np.float64)
    direction = np.empty(n, dtype=np.float64)
    
    # Initialize all arrays with NaN
    for i in range(n):
        upperBand[i] = np.nan
        lowerBand[i] = np.nan
        supertrend[i] = np.nan
        direction[i] = np.nan
    
    # Calculate bands and supertrend
    for i in range(n):
        # Pine Script: upperBand := source + factor * st_atr
        # Pine Script: lowerBand := source - factor * st_atr
        upperBand[i] = source[i] + atr_multiplier * atr[i]
        lowerBand[i] = source[i] - atr_multiplier * atr[i]
        
        # Adjust bands based on previous values (matching Pine Script exactly)
        if i > 0:
            # Pine Script: prevLowerBand = nz(lowerBand[1])
            # Pine Script: prevUpperBand = nz(upperBand[1])
            prev_lowerBand = lowerBand[i-1] if not np.isnan(lowerBand[i-1]) else lowerBand[i]
            prev_upperBand = upperBand[i-1] if not np.isnan(upperBand[i-1]) else upperBand[i]
            prev_hl2 = hl2[i-1]
            
            # Pine Script: lowerBand := lowerBand > prevLowerBand or src[1] < prevLowerBand ? lowerBand : prevLowerBand
            if lowerBand[i] > prev_lowerBand or prev_hl2 < prev_lowerBand:
                lowerBand[i] = lowerBand[i]
            else:
                lowerBand[i] = prev_lowerBand
            
            # Pine Script: upperBand := upperBand < prevUpperBand or src[1] > prevUpperBand ? upperBand : prevUpperBand
            if upperBand[i] < prev_upperBand or prev_hl2 > prev_upperBand:
                upperBand[i] = upperBand[i]
            else:
                upperBand[i] = prev_upperBand
        
        # Determine direction and supertrend (matching Pine Script logic)
        # Pine Script:
        #   if na(st_atr[1])
        #       direction := 1
        #   else if prevSuperTrend == prevUpperBand
        #       direction := src > upperBand ? -1 : 1
        #   else
        #       direction := src < lowerBand ? 1 : -1
        
        if i == 0 or np.isnan(atr[i-1]):
            # Pine Script: if na(st_atr[1]) direction := 1
            direction[i] = 1
        else:
            # Get ADJUSTED previous values
            prev_supertrend = supertrend[i-1]
            prev_upperBand = upperBand[i-1]
            prev_lowerBand = lowerBand[i-1]
            current_hl2 = hl2[i]
            
            # Pine Script: else if prevSuperTrend == prevUpperBand
            if prev_supertrend == prev_upperBand:
                # Pine Script: direction := src > upperBand ? -1 : 1
                if current_hl2 > upperBand[i]:
                    direction[i] = -1  # Switch to downtrend
                else:
                    direction[i] = 1  # Stay in uptrend
            else:
                # Pine Script: direction := src < lowerBand ? 1 : -1
                if current_hl2 < lowerBand[i]:
                    direction[i] = 1  # Switch to uptrend
                else:
                    direction[i] = -1  # Stay in downtrend
        
        # Set supertrend based on direction
        # Pine Script: superTrend := direction == -1 ? lowerBand : upperBand
        if direction[i] == -1:
            supertrend[i] = lowerBand[i]
        else:
            supertrend[i] = upperBand[i]
    
    return supertrend, direction, upperBand, lowerBand


@njit(cache=True)
def _calculate_sma_numba(values: np.ndarray, period: int) -> np.ndarray:
    """
    Numba-optimized Simple Moving Average calculation
    Pine Script equivalent: ta.sma(src, period)
    
    Args:
        values: Input array
        period: SMA period
    
    Returns:
        np.ndarray: SMA values
    """
    n = len(values)
    sma = np.empty(n, dtype=np.float64)
    
    for i in range(n):
        if i < period - 1:
            # For the first period-1 values, use expanding window
            sma[i] = np.mean(values[:i+1])
        else:
            # Use rolling window
            sma[i] = np.mean(values[i-period+1:i+1])
    
    return sma


def _calculate_supertrend_worker(args: tuple) -> Tuple[str, pd.DataFrame, Dict]:
    """
    Worker function for parallel supertrend calculation
    Must be at module level for pickling (multiprocessing requirement)
    
    Args:
        args: (symbol, dataframe, configs_list)
    
    Returns:
        Tuple: (symbol, calculated_dataframe, state_variables)
    """
    symbol, df, configs = args
    
    try:
        # Create calculator instance in worker process
        calculator = SupertrendCalculator()
        
        # Calculate all supertrends for this symbol
        df_with_st = calculator.calculate_multiple_supertrends(df, configs)
        
        # Extract state variables
        symbol_state = {}
        for config in configs:
            config_state = calculator.get_state_variables(df_with_st, config['name'])
            symbol_state.update(config_state)
        
        return symbol, df_with_st, symbol_state
        
    except Exception as e:
        logger.error(f"Worker error for {symbol}: {e}")
        return symbol, None, {}


class SupertrendCalculator:
    """
    Calculate custom Supertrend indicator matching Pine Script logic EXACTLY
    Optimized with Numba for high performance
    
    Pine Script Reference:
    - HL2 = (high + low) / 2
    - ATR = ta.atr() uses RMA (exponential moving average)
    - use_sma parameter: When True, use SMA of HL2; when False, use raw HL2
    - direction: -1 (price below supertrend, LONG), 1 (price above supertrend, SHORT)
    """
    
    def __init__(self):
        """Initialize Supertrend Calculator"""
        self.atr_calculator = ATRCalculator()
    
    def calculate_supertrend(
        self,
        df: pd.DataFrame,
        atr_period: int = 15,
        atr_multiplier: float = 2.0,
        use_sma: bool = True,
        config_name: str = "supertrend"
    ) -> pd.DataFrame:
        """
        Calculate supertrend indicator matching Pine Script exactly
        
        Args:
            df: DataFrame with OHLC data (must have 'high', 'low', 'close', 'hl2')
            atr_period: Period for ATR calculation
            atr_multiplier: Multiplier for ATR bands (factor in Pine Script)
            use_sma: If True, use SMA of HL2 (use_ema=true in Pine); if False, use raw HL2
            config_name: Name for the configuration (for column naming)
        
        Returns:
            pd.DataFrame: DataFrame with supertrend columns added
        """
        df = df.copy()
        
        # Validate input data
        required_cols = ['high', 'low', 'close', 'hl2']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                return df
        
        # Calculate ATR using RMA (like Pine Script's ta.atr())
        atr = self.atr_calculator.calculate_atr(
            df['high'],
            df['low'],
            df['close'],
            period=atr_period
        )
        
        # Calculate source (HL2 with or without SMA)
        if use_sma:
            # Use SMA of HL2 (when use_ema=true in Pine Script)
            hl2_np = df['hl2'].values
            source_np = _calculate_sma_numba(hl2_np, atr_period)
        else:
            # Use raw HL2 (when use_ema=false in Pine Script)
            source_np = df['hl2'].values
        
        # Convert to numpy arrays for Numba processing
        high_np = df['high'].values
        low_np = df['low'].values
        close_np = df['close'].values
        hl2_np = df['hl2'].values
        atr_np = atr.values
        
        # Calculate supertrend using Numba-optimized function
        supertrend_np, direction_np, upperBand_np, lowerBand_np = _calculate_supertrend_numba(
            high_np, low_np, close_np, hl2_np, atr_np, source_np, atr_multiplier
        )
        
        # Add columns to dataframe
        df[f'supertrend_{config_name}'] = supertrend_np
        df[f'direction_{config_name}'] = direction_np
        df[f'upperBand_{config_name}'] = upperBand_np
        df[f'lowerBand_{config_name}'] = lowerBand_np
        
        # Validate the calculation
        is_valid, message = DataValidator.validate_supertrend_calculation(
            df,
            f'supertrend_{config_name}',
            f'direction_{config_name}',
            atr_period=atr_period
        )
        
        if not is_valid:
            logger.warning(f"Supertrend validation warning for {config_name}: {message}")
        
        return df
    
    def calculate_multiple_supertrends(
        self,
        df: pd.DataFrame,
        configs: list
    ) -> pd.DataFrame:
        """
        Calculate multiple supertrend configurations on the same DataFrame
        
        Args:
            df: DataFrame with OHLC data
            configs: List of config dictionaries with keys:
                    - 'name': configuration name
                    - 'atr_period': ATR period
                    - 'atr_multiplier': ATR multiplier
                    - 'use_sma': whether to use SMA of HL2
        
        Returns:
            pd.DataFrame: DataFrame with all supertrend configurations
        """
        for config in configs:
            name = config['name']
            df = self.calculate_supertrend(
                df,
                atr_period=config['atr_period'],
                atr_multiplier=config['atr_multiplier'],
                use_sma=config['use_sma'],
                config_name=name
            )
        
        return df
    
    def get_state_variables(
        self,
        df: pd.DataFrame,
        config_name: str
    ) -> Dict:
        """
        Extract state variables for incremental calculation
        
        Args:
            df: DataFrame with calculated supertrend
            config_name: Name of the supertrend configuration
        
        Returns:
            Dict: State variables for future incremental updates
        """
        if df.empty:
            return {}
        
        last_idx = len(df) - 1
        
        state = {
            f'prev_supertrend_{config_name}': df[f'supertrend_{config_name}'].iloc[last_idx],
            f'prev_upperBand_{config_name}': df[f'upperBand_{config_name}'].iloc[last_idx],
            f'prev_lowerBand_{config_name}': df[f'lowerBand_{config_name}'].iloc[last_idx],
            f'prev_direction_{config_name}': df[f'direction_{config_name}'].iloc[last_idx],
            f'prev_hl2_{config_name}': df['hl2'].iloc[last_idx],
            f'prev_close_{config_name}': df['close'].iloc[last_idx]
        }
        
        return state
    
    def calculate_with_state_preservation(
        self,
        df_by_symbol: Dict[str, pd.DataFrame],
        configs: list,
        timeframe: str,
        use_parallel: bool = True,
        max_workers: Optional[int] = None
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
        """
        Calculate supertrends for all symbols with optional parallel processing
        
        Args:
            df_by_symbol: Dictionary mapping symbol to DataFrame
            configs: List of supertrend configurations
            timeframe: Timeframe identifier
            use_parallel: Whether to use parallel processing (default: True)
            max_workers: Number of parallel workers (default: CPU count)
        
        Returns:
            Tuple: (calculated_dataframes, state_variables_by_symbol)
        """
        num_symbols = len(df_by_symbol)
        
        # Determine if parallel processing is beneficial
        # For small datasets (<50 symbols), sequential is faster due to overhead
        if not use_parallel or num_symbols < 50:
            logger.info(f"Calculating supertrends sequentially for {num_symbols} symbols (Numba-optimized)...")
            return self._calculate_sequential(df_by_symbol, configs, timeframe)
        
        # Use parallel processing for larger datasets
        if max_workers is None:
            max_workers = max(1, cpu_count() - 1)  # Leave one core free
        logger.info(f'Number of CPU counts available : {max_workers}')   
         
        # Cap workers at reasonable maximum
        max_workers = min(max_workers, num_symbols, 16)
    
        logger.info(f"Calculating supertrends for {num_symbols} symbols using {max_workers} parallel workers (Numba-optimized)...")
        
        return self._calculate_parallel(df_by_symbol, configs, timeframe, max_workers)
    
    def _calculate_sequential(
        self,
        df_by_symbol: Dict[str, pd.DataFrame],
        configs: list,
        timeframe: str
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
        """Sequential calculation (original implementation)"""
        calculated_dfs = {}
        states = {}
        
        progress = ProgressLogger(len(df_by_symbol), f"Calculating {timeframe} supertrends", logger)
        
        for symbol, df in df_by_symbol.items():
            if df.empty:
                logger.warning(f"{symbol}: Empty dataframe, skipping")
                progress.update()
                continue
            
            # Calculate all supertrends for this symbol
            df_with_st = self.calculate_multiple_supertrends(df, configs)
            calculated_dfs[symbol] = df_with_st
            
            # Extract state variables for all configs
            symbol_state = {}
            for config in configs:
                config_state = self.get_state_variables(df_with_st, config['name'])
                symbol_state.update(config_state)
            
            states[symbol] = symbol_state
            progress.update()
        
        progress.complete(f"Calculated supertrends for {len(calculated_dfs)} symbols")
        
        return calculated_dfs, states
    
    def _calculate_parallel(
        self,
        df_by_symbol: Dict[str, pd.DataFrame],
        configs: list,
        timeframe: str,
        max_workers: int
    ) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Dict]]:
        """Parallel calculation using ProcessPoolExecutor"""
        calculated_dfs = {}
        states = {}
        
        # Prepare arguments for parallel processing
        args_list = [
            (symbol, df, configs)
            for symbol, df in df_by_symbol.items()
            if not df.empty
        ]
        
        if not args_list:
            logger.warning("No valid data to process")
            return {}, {}
        
        try:
            # Use ProcessPoolExecutor for parallel processing
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # Submit all jobs
                future_to_symbol = {
                    executor.submit(_calculate_supertrend_worker, args): args[0]
                    for args in args_list
                }
                
                # Collect results with progress tracking
                completed = 0
                failed = 0
                total = len(future_to_symbol)
                last_percentage = -1
                
                for future in as_completed(future_to_symbol):
                    symbol = future_to_symbol[future]
                    try:
                        result_symbol, df_with_st, symbol_state = future.result()
                        
                        if df_with_st is not None and not df_with_st.empty:
                            calculated_dfs[result_symbol] = df_with_st
                            states[result_symbol] = symbol_state
                            completed += 1
                        else:
                            failed += 1
                            logger.warning(f"{result_symbol}: Calculation returned empty result")
                        
                    except Exception as e:
                        failed += 1
                        logger.error(f"{symbol}: Calculation failed - {e}")
                    
                    # Update progress - show percentage every 10%
                    total_processed = completed + failed
                    percentage = int((total_processed / total) * 100)
                    if percentage >= last_percentage + 10 or total_processed == total:
                        logger.info(f"Progress: {total_processed}/{total} ({percentage}%)")
                        last_percentage = percentage
                
                logger.info(f"Calculation complete: Success: {completed}, Failed: {failed}, Total: {total}")
        
        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            logger.info("Falling back to sequential processing...")
            return self._calculate_sequential(df_by_symbol, configs, timeframe)
        
        return calculated_dfs, states