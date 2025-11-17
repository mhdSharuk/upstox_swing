"""
Configuration settings for Upstox Supertrend Project
"""

# ==================== UPSTOX API CONFIGURATION ====================
API_CONFIG = {
    'token_file': 'upstox_token.json',
    'base_url': 'https://api.upstox.com',
    'historical_endpoint': '/v3/historical-candle',
    'instruments_url': 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz',
    'rate_limit_delay': 0.1,  # Delay between API calls in seconds
    'max_retries': 3,
    'retry_delay': 2
}

# ==================== TIMEFRAME CONFIGURATIONS ====================
TIMEFRAME_CONFIG = {
    '125min': {
        'unit': 'minutes',
        'interval': 125,
        'days_history': 90,  # Upstox limit for >15min intervals
        'candles_per_day': 3  # Approximately 3 candles per trading day
    },
    'daily': {
        'unit': 'days',
        'interval': 1,
        'days_history': 365,  # 3 years
        'candles_per_year': 252  # Approximately 252 trading days per year
    }
}

# ==================== SUPERTREND CONFIGURATIONS ====================
# 125-minute timeframe configurations
SUPERTREND_CONFIGS_125M = [
    {
        'name': 'ST_125m_sma15',
        'use_sma': True,
        'atr_period': 15,
        'atr_multiplier': 2.0,
        'description': 'Weekly reference with SMA (3 candles/day × 5 days)'
    },
    {
        'name': 'ST_125m_hl2',
        'use_sma': False,
        'atr_period': 15,
        'atr_multiplier': 2.0,
        'description': 'Weekly reference without SMA'
    }
]

# Daily timeframe configurations
SUPERTREND_CONFIGS_DAILY = [
    {
        'name': 'ST_daily_sma5',
        'use_sma': True,
        'atr_period': 5,
        'atr_multiplier': 2.0,
        'description': 'Weekly reference with SMA (5 trading days/week)'
    },
    {
        'name': 'ST_daily_sma20',
        'use_sma': True,
        'atr_period': 20,
        'atr_multiplier': 2.0,
        'description': 'Monthly reference with SMA (~20 trading days/month)'
    },
    {
        'name': 'ST_daily_hl2_20',
        'use_sma': False,
        'atr_period': 20,
        'atr_multiplier': 2.0,
        'description': 'Monthly reference without SMA'
    },
    {
        'name': 'ST_daily_hl2_5',
        'use_sma': False,
        'atr_period': 5,
        'atr_multiplier': 2.0,
        'description': 'Weekly reference without SMA'
    }
]

# ==================== DATA RETENTION SETTINGS ====================
CANDLE_RETENTION = {
    '125min': 3,  # Keep latest 3 candles per symbol
    'daily': 3     # Keep latest 3 candles per symbol
}

# ==================== FLAT BASE DETECTION ====================
FLAT_BASE_TOLERANCE = 0.001  # Exactly 0.1% tolerance
FLAT_BASE_MIN_COUNT = 3      # Minimum consecutive candles to count as flat base

# ==================== GOOGLE SHEETS CONFIGURATION ====================
SHEETS_CONFIG = {
    'sheet_id': '1c2D3KERJJSJIDRO6hzVVsiasAN3uXyypESMkThxWVZo',  # To be set by user
    'service_account_file': 'service_account.json',
    'sheet_names': {
        '125min': '125min_data',
        'daily': 'daily_data'
    },
    'batch_size': 2500,  # Number of rows to write per batch
    'max_retries': 3
}

# ==================== INSTRUMENT FILTERING ====================
INSTRUMENT_FILTERS = {
    'instrument_types': ['EQ'],  # Equity types
    'key_pattern': 'INE',  # Must contain INE in instrument_key
    'exchange': 'NSE_EQ'  # Focus on NSE equity
}

# ==================== ASYNC PROCESSING ====================
ASYNC_CONFIG = {
    'max_concurrent_requests': 40,  # Maximum concurrent API requests
    'chunk_size': 50,  # Process instruments in chunks
    'semaphore_limit': 40  # Limit concurrent operations
}

# ==================== LOGGING CONFIGURATION ====================
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'upstox_supertrend.log',
    'console': True
}

# ==================== STATE VARIABLES TEMPLATE ====================
STATE_VARIABLES_TEMPLATE = {
    'prev_supertrend': None,
    'prev_upperBand': None,
    'prev_lowerBand': None,
    'prev_direction': None,
    'prev_hl2': None,
    'prev_close': None,
    'atr_components': [],  # For ATR calculation rolling window
    'sma_sum': None,       # For SMA calculation
    'sma_count': None      # For SMA calculation
}