"""
Settings and configurations for the Upstox Supertrend Project
Contains timeframe configs, indicator parameters, and API settings
UPDATED: Supabase Storage configuration (Google Sheets/Drive removed)
UPDATED: Added PythonAnywhere deployment configuration
"""

# ==================== PYTHONANYWHERE CONFIGURATION ====================
PYTHONANYWHERE_CONFIG = {
    'username': 'mhdsharuk',
    'base_url': 'https://mhdsharuk.pythonanywhere.com',
    'redirect_uri': 'https://mhdsharuk.pythonanywhere.com/callback',
}

# ==================== UPSTOX API CONFIGURATION ====================
API_CONFIG = {
    'base_url': 'https://api.upstox.com',
    'historical_endpoint': '/v3/historical-candle',
    'intraday_endpoint': '/v3/historical-candle/intraday',
    'market_status_endpoint': '/v2/market/status',
    'instruments_url': 'https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz',
    'rate_limit_delay': 0.1,
    'max_retries': 3,
    'retry_delay': 2,
    'timeout': 30
}

# ==================== TIMEFRAME CONFIGURATION ====================
TIMEFRAME_CONFIG = {
    '125min': {
        'unit': 'minutes',
        'interval': 125,
        'days_history': 90,
        'candles_per_day': 3
    },
    'daily': {
        'unit': 'days',
        'interval': 1,
        'days_history': 365,
        'candles_per_year': 252
    }
}

# ==================== SUPERTREND CONFIGURATIONS ====================
SUPERTREND_CONFIGS_125M = [
    {
        'name': 'ST_125m_sma15',
        'use_sma': True,
        'atr_period': 15,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference with SMA'
    },
    {
        'name': 'ST_125m_hl2_15',
        'use_sma': False,
        'atr_period': 15,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference without SMA'
    },
]

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
]

# ==================== DATA RETENTION SETTINGS ====================
PARQUET_RETENTION = {
    '125min': 400,
    'daily': 400
}

# ==================== SUPABASE CONFIGURATION ====================
SUPABASE_CONFIG = {
    'bucket_name': 'st-swing-bucket',
    'file_names': {
        '125min': '125min.parquet',
        'daily': 'daily.parquet'
    }
}

# ==================== FLAT BASE DETECTION ====================
FLAT_BASE_TOLERANCE = 0.001
FLAT_BASE_MIN_COUNT = 3

# ==================== INSTRUMENT FILTERING ====================
INSTRUMENT_FILTERS = {
    'instrument_types': ['EQ'],
    'key_pattern': 'INE',
    'exchange': 'NSE_EQ',
    'min_market_cap': 5000
}

# ==================== SYMBOL INFO CSV ====================
SYMBOL_INFO_CONFIG = {
    'url': 'https://docs.google.com/spreadsheets/d/1meVDXRT2eGBdmc1kRmtWiUd7iP-Ik1sxQHC_O4rz8K8/gviz/tq?tqx=out:csv&gid=1767398927',
    'required_columns': ['trading_symbol', 'sector', 'industry', 'market_cap']
}

# ==================== ASYNC PROCESSING ====================
ASYNC_CONFIG = {
    'max_concurrent_requests': 10,
    'chunk_size': 50,
    'semaphore_limit': 10
}

# ==================== LOGGING CONFIGURATION ====================
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/upstox_supertrend.log',
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
    'atr_components': [],
    'sma_sum': None,
    'sma_count': None
}