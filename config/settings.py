"""
Settings and configurations for the Upstox Supertrend Project
Contains timeframe configs, indicator parameters, and API settings
COMPLETE VERSION - All required fields included
"""

# ==================== UPSTOX API CONFIGURATION ====================
API_CONFIG = {
    'base_url': 'https://api.upstox.com',
    'historical_endpoint': '/v3/historical-candle',
    'intraday_endpoint': '/v3/historical-candle/intraday',
    'market_status_endpoint': '/v2/market/status',
    'instruments_url': 'https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz',
    'rate_limit_delay': 0.1,  # Delay between API calls in seconds
    'max_retries': 3,
    'retry_delay': 2,
    'timeout': 30
}

# ==================== TIMEFRAME CONFIGURATION ====================
# Based on Upstox v3 API: /v3/historical-candle/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}
# Unit options: 'minutes', 'hours', 'days', 'weeks', 'months'
# Interval: numeric value (1-300 for minutes, 1-5 for hours, 1 for days/weeks/months)
TIMEFRAME_CONFIG = {
    '125min': {
        'unit': 'minutes',   # Unit for API (minutes, hours, days, etc.)
        'interval': 125,      # Interval value (125 minutes)
        'days_history': 90,   # Max history: 1 quarter for intervals > 15 minutes
        'candles_per_day': 3  # Approximately 3 candles per trading day
    },
    'daily': {
        'unit': 'days',      # Unit for API
        'interval': 1,        # Interval value (1 day)
        'days_history': 365,  # Max history: 1 decade for days
        'candles_per_year': 252  # Approximately 252 trading days per year
    }
}

# ==================== SUPERTREND CONFIGURATIONS ====================
# 125-minute timeframe configurations
SUPERTREND_CONFIGS_125M = [
    {
        'name': 'ST_125m_sma3',
        'use_sma': True,
        'atr_period': 3,
        'atr_multiplier': 2.0,
        'description': 'Short-term reference with SMA'
    },
    {
        'name': 'ST_125m_sma10',
        'use_sma': True,
        'atr_period': 10,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference with SMA'
    },
    {
        'name': 'ST_125m_hl2_10',
        'use_sma': False,
        'atr_period': 10,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference without SMA'
    },
    {
        'name': 'ST_125m_hl2_3',
        'use_sma': False,
        'atr_period': 3,
        'atr_multiplier': 2.0,
        'description': 'Short-term reference without SMA'
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
# Retention for Google Sheets (preview data)
CANDLE_RETENTION = {
    '125min': 3,  # Keep latest 3 candles per symbol
    'daily': 3     # Keep latest 3 candles per symbol
}

# Retention for Parquet files (historical archive)
PARQUET_RETENTION = {
    '125min': 120,  # Keep latest 120 candles per symbol
    'daily': 120     # Keep latest 120 candles per symbol
}

# ==================== GOOGLE DRIVE CONFIGURATION ====================
DRIVE_CONFIG = {
    'folder_name': 'Upstox Parquet Data',  # Folder name in Google Drive
    'folder_id': None,  # IMPORTANT: Add your shared folder ID here (see instructions)
    'oauth_credentials_file': 'credentials/oauth_credentials.json',  # OAuth2 client credentials
    'oauth_token_file': 'credentials/drive_oauth_token.json',  # OAuth2 access/refresh tokens
    'file_names': {
        '125min': '125min.parquet',
        'daily': 'daily.parquet'
    }
}

# ==================== FLAT BASE DETECTION ====================
FLAT_BASE_TOLERANCE = 0.001  # Exactly 0.1% tolerance
FLAT_BASE_MIN_COUNT = 3      # Minimum consecutive candles to count as flat base

# ==================== GOOGLE SHEETS CONFIGURATION ====================
SHEETS_CONFIG = {
    'sheet_id': '1c2D3KERJJSJIDRO6hzVVsiasAN3uXyypESMkThxWVZo',  # To be set by user
    'service_account_file': 'credentials/service_account.json',
    'sheet_names': {
        '125min': '125min',
        'daily': 'Daily'
    },
    'batch_size': 500,
    'max_retries': 3
}

# ==================== INSTRUMENT FILTERING ====================
INSTRUMENT_FILTERS = {
    'instrument_types': ['EQ'],  # Equity types
    'key_pattern': 'INE',  # Must contain INE in instrument_key
    'exchange': 'NSE_EQ',  # Focus on NSE equity
    'min_market_cap': 1000  # Minimum market cap in Crores
}

# ==================== SYMBOL INFO CSV ====================
SYMBOL_INFO_CONFIG = {
    'url': 'https://docs.google.com/spreadsheets/d/1meVDXRT2eGBdmc1kRmtWiUd7iP-Ik1sxQHC_O4rz8K8/gviz/tq?tqx=out:csv&gid=1767398927',
    'required_columns': ['trading_symbol', 'sector', 'industry', 'market_cap']
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
    'atr_components': [],  # For ATR calculation rolling window
    'sma_sum': None,       # For SMA calculation
    'sma_count': None      # For SMA calculation
}