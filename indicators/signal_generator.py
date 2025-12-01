"""
Signal Generator for Trading Strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class SignalGenerator:
    
    TIMEFRAME_CONFIGS = {
        '60min': {
            'longer': 'ST_60m_sma35',
            'shorter': 'ST_60m_sma7'
        },
        '125min': {
            'longer': 'ST_125m_sma15',
            'shorter': 'ST_125m_sma3'
        },
        'daily': {
            'longer': 'ST_daily_sma20',
            'shorter': 'ST_daily_sma5'
        }
    }
    
    PCT_DIFF_THRESHOLD = 10.0
    LOOKBACK_CANDLES = 10
    
    def __init__(self):
        pass
    
    def generate_signals(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if timeframe not in self.TIMEFRAME_CONFIGS:
            logger.error(f"Invalid timeframe: {timeframe}")
            return pd.DataFrame()
        
        config = self.TIMEFRAME_CONFIGS[timeframe]
        longer_name = config['longer']
        shorter_name = config['shorter']
        
        logger.info(f"Generating signals for {timeframe}...")
        logger.info(f"  Longer config: {longer_name}")
        logger.info(f"  Shorter config: {shorter_name}")
        
        df_baseline = self._apply_baseline_filter(df, longer_name)
        
        if df_baseline.empty:
            logger.info(f"  No stocks passed baseline filter for {timeframe}")
            return pd.DataFrame()
        
        logger.info(f"  Stocks after baseline filter: {df_baseline['trading_symbol'].nunique()}")
        
        df_signals = self._apply_strategy_filters(df_baseline, shorter_name)
        
        logger.info(f"  Final stocks with signals: {df_signals['trading_symbol'].nunique()}")
        logger.info(f"  Volatility Breakout: {df_signals['is_volatility_breakout'].sum()}")
        logger.info(f"  Volatility Support: {df_signals['is_volatility_support'].sum()}")
        
        return df_signals
    
    def _apply_baseline_filter(self, df: pd.DataFrame, longer_name: str) -> pd.DataFrame:
        direction_col = f'direction_{longer_name}'
        
        if direction_col not in df.columns:
            logger.error(f"Column {direction_col} not found")
            return pd.DataFrame()
        
        df_filtered = df[df[direction_col] == -1].copy()
        
        return df_filtered
    
    def _apply_strategy_filters(self, df: pd.DataFrame, shorter_name: str) -> pd.DataFrame:
        direction_col = f'direction_{shorter_name}'
        supertrend_col = f'supertrend_{shorter_name}'
        upperband_col = f'upperBand_{shorter_name}'
        lowerband_col = f'lowerBand_{shorter_name}'
        pct_col = f'pct_diff_{shorter_name}'
        
        required_cols = [direction_col, supertrend_col, upperband_col, lowerband_col, 'close', 'timestamp']
        
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Required column {col} not found")
                return pd.DataFrame()
        
        df_sorted = df.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
        
        results = []
        
        for symbol in df_sorted['trading_symbol'].unique():
            symbol_df = df_sorted[df_sorted['trading_symbol'] == symbol].reset_index(drop=True)
            
            if len(symbol_df) == 0:
                continue
            
            latest_idx = len(symbol_df) - 1
            latest_row = symbol_df.iloc[latest_idx]
            
            is_breakout, breakout_date = self._check_volatility_breakout(
                symbol_df, latest_idx, direction_col, upperband_col, supertrend_col
            )
            
            is_support = self._check_volatility_support(
                latest_row, lowerband_col, pct_col
            )
            
            if is_breakout or is_support:
                row_data = latest_row.copy()
                row_data['is_volatility_breakout'] = is_breakout
                row_data['is_volatility_support'] = is_support
                row_data['breakout_trigger_date'] = breakout_date if is_breakout else None
                results.append(row_data)
        
        if not results:
            return pd.DataFrame()
        
        df_signals = pd.DataFrame(results)
        
        return df_signals
    
    def _check_volatility_breakout(
        self, 
        symbol_df: pd.DataFrame, 
        latest_idx: int,
        direction_col: str,
        upperband_col: str,
        supertrend_col: str
    ) -> Tuple[bool, pd.Timestamp]:
        
        latest_row = symbol_df.iloc[latest_idx]
        latest_direction = latest_row[direction_col]
        latest_close = latest_row['close']
        latest_supertrend = latest_row[supertrend_col]
        
        if latest_direction == 1 and latest_close < latest_supertrend:
            return False, None
        
        start_idx = max(0, latest_idx - self.LOOKBACK_CANDLES + 1)
        lookback_df = symbol_df.iloc[start_idx:latest_idx + 1]
        
        triggered_candles = lookback_df[
            (lookback_df[direction_col] == -1) & 
            (lookback_df['close'] > lookback_df[upperband_col])
        ]
        
        if len(triggered_candles) > 0:
            breakout_date = triggered_candles.iloc[0]['timestamp']
            return True, breakout_date
        
        return False, None
    
    def _check_volatility_support(
        self,
        latest_row: pd.Series,
        lowerband_col: str,
        pct_col: str
    ) -> bool:
        
        if pct_col in latest_row.index and pd.notna(latest_row[pct_col]):
            pct_diff = latest_row[pct_col]
        else:
            close = latest_row['close']
            lowerband = latest_row[lowerband_col]
            
            if pd.isna(lowerband) or lowerband == 0:
                return False
            
            pct_diff = ((close - lowerband) / close) * 100
        
        if abs(pct_diff) < self.PCT_DIFF_THRESHOLD:
            return True
        
        return False
    
    def generate_all_timeframes(
        self, 
        data_dict: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        
        logger.info("\n" + "=" * 60)
        logger.info("GENERATING TRADING SIGNALS")
        logger.info("=" * 60)
        
        signals_dict = {}
        
        for timeframe in ['60min', '125min', 'daily']:
            if timeframe not in data_dict:
                logger.warning(f"Timeframe {timeframe} not found in data")
                continue
            
            df = data_dict[timeframe]
            signals = self.generate_signals(df, timeframe)
            
            if not signals.empty:
                signals_dict[timeframe] = signals
            else:
                logger.warning(f"No signals generated for {timeframe}")
        
        logger.info("\n" + "=" * 60)
        logger.info("SIGNAL GENERATION COMPLETE")
        logger.info("=" * 60)
        
        return signals_dict