"""
ATR (Average True Range) Calculator - Optimized with NumPy vectorization
Pine Script's ta.atr() uses RMA (Rolling Moving Average / Exponential MA)
"""

import pandas as pd
import numpy as np
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ATRCalculator:
    """
    Calculate Average True Range (ATR) indicator matching Pine Script's ta.atr()
    Optimized with vectorized NumPy operations
    """
    
    @staticmethod
    def calculate_true_range(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """
        Calculate True Range using vectorized operations
        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
        
        Returns:
            pd.Series: True Range values
        """
        # Calculate three components
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        
        # Get maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return true_range
    
    @staticmethod
    def calculate_rma(values: pd.Series, period: int) -> pd.Series:
        """
        Calculate RMA (Rolling Moving Average) - equivalent to EMA with alpha=1/period
        This matches Pine Script's ta.atr() implementation
        
        Args:
            values: Input series
            period: Period for RMA
        
        Returns:
            pd.Series: RMA values
        """
        # RMA is equivalent to EMA with alpha = 1/period
        alpha = 1.0 / period
        
        # Use pandas ewm (exponentially weighted moving average)
        rma = values.ewm(alpha=alpha, adjust=False).mean()
        
        return rma
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate ATR using RMA (like Pine Script's ta.atr())
        
        Args:
            high: High prices
            low: Low prices
            close: Close prices
            period: ATR period (default: 14)
        
        Returns:
            pd.Series: ATR values
        """
        # Calculate True Range
        true_range = ATRCalculator.calculate_true_range(high, low, close)
        
        # Calculate ATR using RMA
        atr = ATRCalculator.calculate_rma(true_range, period)
        
        return atr
    
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
        # Calculate True Range
        true_range = ATRCalculator.calculate_true_range(high, low, close)
        
        # If we have previous state, prepend it
        if prev_atr_components:
            prev_tr = pd.Series(prev_atr_components)
            true_range = pd.concat([prev_tr, true_range], ignore_index=True)
        
        # Calculate ATR using RMA
        atr = ATRCalculator.calculate_rma(true_range, period)
        
        # Extract state (last 'period' values of true range)
        state_components = true_range.iloc[-period:].tolist()
        
        # If we had prepended previous state, remove it from result
        if prev_atr_components:
            atr = atr.iloc[len(prev_atr_components):]
            atr.index = high.index
        
        return atr, state_components