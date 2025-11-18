"""
Configuration package for Upstox Supertrend Project
Exports all configuration variables for use across the application
"""

from .settings import (
    # API Configuration
    API_CONFIG,
    
    # Timeframe Configuration
    TIMEFRAME_CONFIG,
    
    # Supertrend Configurations
    SUPERTREND_CONFIGS_125M,
    SUPERTREND_CONFIGS_DAILY,
    
    # Retention Settings
    CANDLE_RETENTION,
    PARQUET_RETENTION,
    
    # Google Drive Configuration
    DRIVE_CONFIG,
    
    # Flat Base Detection
    FLAT_BASE_TOLERANCE,
    FLAT_BASE_MIN_COUNT,
    
    # Google Sheets Configuration
    SHEETS_CONFIG,
    
    # Instrument Filtering
    INSTRUMENT_FILTERS,
    
    # Symbol Info
    SYMBOL_INFO_CONFIG,
    
    # Async Configuration
    ASYNC_CONFIG,
    
    # Logging Configuration
    LOGGING_CONFIG,
    
    # State Variables Template
    STATE_VARIABLES_TEMPLATE
)

__all__ = [
    'API_CONFIG',
    'TIMEFRAME_CONFIG',
    'SUPERTREND_CONFIGS_125M',
    'SUPERTREND_CONFIGS_DAILY',
    'CANDLE_RETENTION',
    'PARQUET_RETENTION',
    'DRIVE_CONFIG',
    'FLAT_BASE_TOLERANCE',
    'FLAT_BASE_MIN_COUNT',
    'SHEETS_CONFIG',
    'INSTRUMENT_FILTERS',
    'SYMBOL_INFO_CONFIG',
    'ASYNC_CONFIG',
    'LOGGING_CONFIG',
    'STATE_VARIABLES_TEMPLATE'
]