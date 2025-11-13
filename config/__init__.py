"""
Configuration package for Upstox Supertrend Project
"""

from .settings import (
    SUPERTREND_CONFIGS_125M,
    SUPERTREND_CONFIGS_DAILY,
    CANDLE_RETENTION,
    FLAT_BASE_TOLERANCE,
    API_CONFIG
)

__all__ = [
    'SUPERTREND_CONFIGS_125M',
    'SUPERTREND_CONFIGS_DAILY',
    'CANDLE_RETENTION',
    'FLAT_BASE_TOLERANCE',
    'API_CONFIG'
]
