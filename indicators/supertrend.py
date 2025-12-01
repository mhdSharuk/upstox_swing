"""
Supertrend Calculator - 100% Pine Script Match
Optimized with vectorized NumPy/Pandas operations
Matches the exact logic from Pine Script sma_supertrend()
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count


def _calculate_supertrend_vectorized(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    hl2: np.ndarray,
    atr: np.ndarray,
    source: np.ndarray,
    atr_multiplier: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Vectorized supertrend calculation matching Pine Script exactly
    
    Pine Script Reference (sma_supertrend):
    ----------------------------------------
    sma_supertrend(factor, volPeriod) =>
        float st_atr = ta.atr(volPeriod)
        src = hl2
        base = ta.sma(src, volPeriod)
        
        float upperBand = base + factor * st_atr
        float lowerBand = base - factor * st_atr
        
        prevLowerBand = nz(lowerBand[1])
        prevUpperBand = nz(upperBand[1])
        
        lowerBand := (lowerBand > prevLowerBand or (src[1] < prevLowerBand and close[1] < prevLowerBand)) ? lowerBand : prevLowerBand
        upperBand := (upperBand < prevUpperBand or (src[1] > prevUpperBand and close[1] > prevUpperBand)) ? upperBand : prevUpperBand

        int direction = na
        float superTrend = na
        prevSuperTrend = superTrend[1]
        
        if na(st_atr[1])
            direction := 1
        else if prevSuperTrend == prevUpperBand
            direction := src > upperBand and close > upperBand ? -1 : 1
        else
            direction := src < lowerBand and close < lowerBand ? 1 : -1

        superTrend := direction == -1 ? lowerBand : upperBand
        
        [superTrend, direction, lowerBand, upperBand]
    
    Args:
        high: High prices array
        low: Low prices array
        close: Close prices array
        hl2: HL2 values array (high + low) / 2
        atr: ATR values array (calculated with RMA/EMA)
        source: Source values - either hl2 OR sma(hl2, period) based on use_sma
        atr_multiplier: Multiplier for ATR bands (factor in Pine Script)
    
    Returns:
        Tuple: (supertrend, direction, upperBand, lowerBand) arrays
    """
    n = len(high)
    
    # Initialize arrays
    upperBand = np.full(n, np.nan, dtype=np.float64)
    lowerBand = np.full(n, np.nan, dtype=np.float64)
    supertrend = np.full(n, np.nan, dtype=np.float64)
    direction = np.full(n, np.nan, dtype=np.float64)
    
    # Pine Script: upperBand := base + factor * st_atr
    # Pine Script: lowerBand := base - factor * st_atr
    upperBand = source + atr_multiplier * atr
    lowerBand = source - atr_multiplier * atr
    
    # Adjust bands based on previous values
    # Pine Script:
    #   prevLowerBand = nz(lowerBand[1])
    #   prevUpperBand = nz(upperBand[1])
    #   lowerBand := (lowerBand > prevLowerBand or (src[1] < prevLowerBand and close[1] < prevLowerBand)) ? lowerBand : prevLowerBand
    #   upperBand := (upperBand < prevUpperBand or (src[1] > prevUpperBand and close[1] > prevUpperBand)) ? upperBand : prevUpperBand
    
    for i in range(1, n):
        # nz(lowerBand[1]) - get previous lowerBand, use current if NaN
        prev_lowerBand = lowerBand[i-1] if not np.isnan(lowerBand[i-1]) else lowerBand[i]
        prev_upperBand = upperBand[i-1] if not np.isnan(upperBand[i-1]) else upperBand[i]
        
        # src[1] and close[1] - previous hl2 and close values
        prev_hl2 = hl2[i-1]
        prev_close = close[i-1]
        
        # Adjust lowerBand
        # lowerBand := (lowerBand > prevLowerBand or (src[1] < prevLowerBand and close[1] < prevLowerBand)) ? lowerBand : prevLowerBand
        if lowerBand[i] > prev_lowerBand or (prev_hl2 < prev_lowerBand and prev_close < prev_lowerBand):
            lowerBand[i] = lowerBand[i]
        else:
            lowerBand[i] = prev_lowerBand
        
        # Adjust upperBand
        # upperBand := (upperBand < prevUpperBand or (src[1] > prevUpperBand and close[1] > prevUpperBand)) ? upperBand : prevUpperBand
        if upperBand[i] < prev_upperBand or (prev_hl2 > prev_upperBand and prev_close > prev_upperBand):
            upperBand[i] = upperBand[i]
        else:
            upperBand[i] = prev_upperBand
    
    # Determine direction and supertrend
    # Pine Script:
    #   prevSuperTrend = superTrend[1]
    #   if na(st_atr[1])
    #       direction := 1
    #   else if prevSuperTrend == prevUpperBand
    #       direction := src > upperBand and close > upperBand ? -1 : 1
    #   else
    #       direction := src < lowerBand and close < lowerBand ? 1 : -1
    #   superTrend := direction == -1 ? lowerBand : upperBand
    
    for i in range(n):
        # if na(st_atr[1])
        if i == 0 or np.isnan(atr[i-1]):
            direction[i] = 1
        else:
            # Get adjusted previous values
            prev_supertrend = supertrend[i-1]
            prev_upperBand = upperBand[i-1]
            current_hl2 = hl2[i]
            current_close = close[i]
            
            # else if prevSuperTrend == prevUpperBand
            if prev_supertrend == prev_upperBand:
                # direction := src > upperBand and close > upperBand ? -1 : 1
                if current_hl2 > upperBand[i] and current_close > upperBand[i]:
                    direction[i] = -1
                else:
                    direction[i] = 1
            else:
                # direction := src < lowerBand and close < lowerBand ? 1 : -1
                if current_hl2 < lowerBand[i] and current_close < lowerBand[i]:
                    direction[i] = 1
                else:
                    direction[i] = -1
        
        # superTrend := direction == -1 ? lowerBand : upperBand
        if direction[i] == -1:
            supertrend[i] = lowerBand[i]
        else:
            supertrend[i] = upperBand[i]
    
    return supertrend, direction, upperBand, lowerBand


def _calculate_sma_vectorized(values: np.ndarray, period: int) -> np.ndarray:
    """
    Vectorized Simple Moving Average calculation
    Pine Script equivalent: ta.sma(src, period)
    
    Args:
        values: Input array
        period: SMA period
    
    Returns:
        np.ndarray: SMA values
    """
    # Use pandas for efficient rolling window
    series = pd.Series(values)
    sma = series.rolling(window=period, min_periods=1).mean().values
    return sma


class SupertrendCalculator:
    """
    Calculate custom Supertrend indicator matching Pine Script logic EXACTLY
    Optimized with vectorized NumPy/Pandas operations
    
    Pine Script Reference:
    - HL2 = (high + low) / 2
    - ATR = ta.atr() uses RMA (exponential moving average with alpha = 1/period)
    - use_sma parameter: When True, use SMA of HL2; when False, use raw HL2
    - direction: -1 (price below supertrend, LONG), 1 (price above supertrend, SHORT)
    
    Note: In Pine Script, the parameter is called 'use_ema' but it actually uses SMA, not EMA.
          We call it 'use_sma' for clarity.
    """
    
    def __init__(self):
        """Initialize Supertrend Calculator"""
        from .atr import ATRCalculator
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
        
        Pine Script equivalent:
        sma_supertrend(atr_multiplier, atr_period)
        
        Args:
            df: DataFrame with OHLC data (must have 'high', 'low', 'close', 'hl2')
            atr_period: Period for ATR calculation (volPeriod in Pine Script)
            atr_multiplier: Multiplier for ATR bands (factor in Pine Script)
            use_sma: If True, use SMA of HL2 (base in Pine); if False, use raw HL2
            config_name: Name for the configuration (for column naming)
        
        Returns:
            pd.DataFrame: DataFrame with supertrend columns added
        """
        df = df.copy()
        
        # Validate input data
        required_cols = ['high', 'low', 'close', 'hl2']
        for col in required_cols:
            if col not in df.columns:
                print(f"ERROR: Missing required column: {col}")
                return df
        
        # Calculate ATR using RMA (like Pine Script's ta.atr())
        # Pine Script: float st_atr = ta.atr(volPeriod)
        atr = self.atr_calculator.calculate_atr(
            df['high'],
            df['low'],
            df['close'],
            period=atr_period
        )
        
        # Calculate source (HL2 with or without SMA)
        # Pine Script: src = hl2
        # Pine Script: base = ta.sma(src, volPeriod)
        if use_sma:
            # Use SMA of HL2 (base in Pine Script)
            source_np = _calculate_sma_vectorized(df['hl2'].values, atr_period)
        else:
            # Use raw HL2
            source_np = df['hl2'].values
        
        # Convert to numpy arrays
        high_np = df['high'].values
        low_np = df['low'].values
        close_np = df['close'].values
        hl2_np = df['hl2'].values
        atr_np = atr.values
        
        # Calculate supertrend using vectorized function
        supertrend_np, direction_np, upperBand_np, lowerBand_np = _calculate_supertrend_vectorized(
            high_np, low_np, close_np, hl2_np, atr_np, source_np, atr_multiplier
        )
        
        # Add columns to dataframe
        df[f'supertrend_{config_name}'] = supertrend_np
        df[f'direction_{config_name}'] = direction_np
        df[f'upperBand_{config_name}'] = upperBand_np
        df[f'lowerBand_{config_name}'] = lowerBand_np
        
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
        
        return {
            f'{config_name}_prev_supertrend': df[f'supertrend_{config_name}'].iloc[last_idx],
            f'{config_name}_prev_upperBand': df[f'upperBand_{config_name}'].iloc[last_idx],
            f'{config_name}_prev_lowerBand': df[f'lowerBand_{config_name}'].iloc[last_idx],
            f'{config_name}_prev_direction': df[f'direction_{config_name}'].iloc[last_idx],
            f'{config_name}_prev_hl2': df['hl2'].iloc[last_idx],
            f'{config_name}_prev_close': df['close'].iloc[last_idx]
        }