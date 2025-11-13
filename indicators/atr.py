"""
ATR (Average True Range) Calculator - Optimized with Numba
Pine Script's ta.atr() uses RMA (Rolling Moving Average / Exponential MA)
"""

import pandas as pd
import numpy as np
from numba import njit
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


@njit(cache=True)
def _calculate_true_range_numba(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """
    Numba-optimized True Range calculation
    TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
    
    Args:
        high: High prices array
        low: Low prices array
        close: Close prices array
    
    Returns:
        np.ndarray: True Range values
    """
    n = len(high)
    true_range = np.empty(n, dtype=np.float64)
    
    # First candle: TR = high - low (no previous close)
    true_range[0] = high[0] - low[0]
    
    # Remaining candles
    for i in range(1, n):
        prev_close = close[i - 1]
        tr1 = high[i] - low[i]
        tr2 = abs(high[i] - prev_close)
        tr3 = abs(low[i] - prev_close)
        true_range[i] = max(tr1, tr2, tr3)
    
    return true_range


@njit(cache=True)
def _calculate_rma_numba(values: np.ndarray, period: int) -> np.ndarray:
    """
    Numba-optimized RMA (Rolling Moving Average) calculation
    RMA is equivalent to EMA with alpha = 1/period
    This matches Pine Script's ta.atr() implementation
    
    Args:
        values: Input array
        period: Period for RMA
    
    Returns:
        np.ndarray: RMA values
    """
    n = len(values)
    rma = np.empty(n, dtype=np.float64)
    alpha = 1.0 / period
    
    # Initialize with first valid value
    rma[0] = values[0]
    
    # Calculate RMA iteratively
    for i in range(1, n):
        if np.isnan(values[i]):
            rma[i] = rma[i - 1]
        else:
            rma[i] = alpha * values[i] + (1.0 - alpha) * rma[i - 1]
    
    return rma


@njit(cache=True)
def _calculate_atr_numba(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int
) -> np.ndarray:
    """
    Numba-optimized ATR calculation using RMA
    
    Args:
        high: High prices array
        low: Low prices array
        close: Close prices array
        period: ATR period
    
    Returns:
        np.ndarray: ATR values
    """
    # Calculate True Range
    true_range = _calculate_true_range_numba(high, low, close)
    
    # Calculate ATR using RMA
    atr = _calculate_rma_numba(true_range, period)
    
    return atr


class ATRCalculator:
    """
    Calculate Average True Range (ATR) indicator matching Pine Script's ta.atr()
    Optimized with Numba for high performance
    """
    
    @staticmethod
    def calculate_true_range(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Calculate True Range
        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
        
        Returns:
            pd.Series: True Range values
        """
        # Convert to numpy arrays for Numba processing
        high_np = high.values
        low_np = low.values
        close_np = close.values
        
        # Calculate using Numba-optimized function
        true_range_np = _calculate_true_range_numba(high_np, low_np, close_np)
        
        # Convert back to pandas Series
        return pd.Series(true_range_np, index=high.index)
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate ATR using RMA (like Pine Script's ta.atr())
        RMA is equivalent to EMA with alpha = 1/period
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default: 14)
        
        Returns:
            pd.Series: ATR values
        """
        # Convert to numpy arrays for Numba processing
        high_np = high.values
        low_np = low.values
        close_np = close.values
        
        # Calculate using Numba-optimized function
        atr_np = _calculate_atr_numba(high_np, low_np, close_np, period)
        
        # Convert back to pandas Series
        return pd.Series(atr_np, index=high.index)
    
    @staticmethod
    def calculate_atr_with_state(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        prev_atr_components: Optional[list] = None
    ) -> tuple[pd.Series, list]:
        """
        Calculate ATR and return state for incremental calculation
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period
            prev_atr_components: Previous ATR window for continuation
        
        Returns:
            tuple: (atr_series, last_atr_components_for_state)
        """
        # Convert to numpy arrays
        high_np = high.values
        low_np = low.values
        close_np = close.values
        
        # Calculate True Range using Numba
        true_range_np = _calculate_true_range_numba(high_np, low_np, close_np)
        
        # If we have previous state, prepend it
        if prev_atr_components:
            true_range_np = np.concatenate([
                np.array(prev_atr_components),
                true_range_np
            ])
        
        # Calculate ATR using RMA
        atr_np = _calculate_rma_numba(true_range_np, period)
        
        # Extract state (last 'period' values of true range)
        state_start = max(0, len(true_range_np) - period)
        state_components = true_range_np[state_start:].tolist()
        
        # If we had prepended previous state, remove it from result
        if prev_atr_components:
            atr_np = atr_np[len(prev_atr_components):]
        
        # Convert back to pandas Series
        atr_series = pd.Series(atr_np, index=high.index)
        
        return atr_series, state_components