"""
Settings and configurations for the Upstox Supertrend Project
UPDATED: Added signal file configuration
"""

PYTHONANYWHERE_CONFIG = {
    'username': 'mhdsharuk',
    'base_url': 'https://mhdsharuk.pythonanywhere.com',
    'redirect_uri': 'https://mhdsharuk.pythonanywhere.com/callback',
}

API_CONFIG = {
    'base_url': 'https://api.upstox.com',
    'historical_endpoint': '/v3/historical-candle',
    'intraday_endpoint': '/v3/historical-candle/intraday',
    'market_status_endpoint': '/v2/market/status',
    'instruments_url': 'https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz',
    'rate_limit_delay': 0.15,
    'max_retries': 3,
    'retry_delay': 2,
    'timeout': 30
}

TIMEFRAME_CONFIG = {
    '60min': {
        'unit': 'minutes',
        'interval': 60,
        'days_history': 60,
        'candles_per_day': 7
    },
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

SUPERTREND_CONFIGS_125M = [
    {
        'name': 'ST_125m_sma15',
        'use_sma': True,
        'atr_period': 15,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference with SMA'
    },
    {
        'name': 'ST_125m_sma3',
        'use_sma': True,
        'atr_period': 3,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference with SMA'
    }
]

SUPERTREND_CONFIGS_60M = [
    {
        'name': 'ST_60m_sma35',
        'use_sma': True,
        'atr_period': 35,
        'atr_multiplier': 2.0,
        'description': 'Long-term reference with SMA'
    },
    {
        'name': 'ST_60m_sma7',
        'use_sma': True,
        'atr_period': 7,
        'atr_multiplier': 2.0,
        'description': 'Medium-term reference with SMA'
    }
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

PARQUET_RETENTION = {
    '60min': 60,
    '125min': 60,
    'daily': 60
}

SUPABASE_CONFIG = {
    'bucket_name': 'st-swing-bucket',
    'file_names': {
        '60min': '60min.parquet',
        '125min': '125min.parquet',
        'daily': 'daily.parquet',
        '60min_signals': '60min_signals.parquet',
        '125min_signals': '125min_signals.parquet',
        'daily_signals': 'daily_signals.parquet'
    }
}

FLAT_BASE_TOLERANCE = 0.001
FLAT_BASE_MIN_COUNT = 3

INSTRUMENT_FILTERS = {
    'instrument_types': ['EQ'],
    'key_pattern': 'INE',
    'exchange': 'NSE_EQ',
    'min_market_cap': 5000
}

SYMBOL_INFO_CONFIG = {
    'url': 'https://docs.google.com/spreadsheets/d/1meVDXRT2eGBdmc1kRmtWiUd7iP-Ik1sxQHC_O4rz8K8/gviz/tq?tqx=out:csv&gid=1767398927',
    'required_columns': ['trading_symbol', 'sector', 'industry', 'market_cap']
}

ASYNC_CONFIG = {
    'max_concurrent_requests': 40,
    'chunk_size': 50,
    'semaphore_limit': 40
}

LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/upstox_supertrend.log',
    'console': True
}

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