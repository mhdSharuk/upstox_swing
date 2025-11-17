"""
Configuration settings for Signal Tracker Streamlit App
"""

# Google Sheets Configuration
SPREADSHEET_ID = "1c2D3KERJJSJIDRO6hzVVsiasAN3uXyypESMkThxWVZo"  # Replace with your actual spreadsheet ID

# Sheet Names
DAILY_DATA_SHEET = "daily_data"
MIN125_DATA_SHEET = "125min_data"
WATCHLIST_SHEET = "Watchlist"

# Cache TTL (seconds)
CACHE_TTL_SIGNALS = 900  # 15 minutes
CACHE_TTL_WATCHLIST = 60  # 1 minute

# Default Filter Values
DEFAULT_MCAP = 10000
DEFAULT_PCT_DIFF = 2.5
DEFAULT_FLATBASE = 3

# Market Hours (IST)
MARKET_START_HOUR = 9
MARKET_START_MINUTE = 15
MARKET_END_HOUR = 15
MARKET_END_MINUTE = 30

# Auto-refresh interval during market hours (milliseconds)
AUTO_REFRESH_INTERVAL = 900000  # 15 minutes

# Watchlist Column Structure
WATCHLIST_DAILY_START_COL = 0  # Column A (0-indexed)
WATCHLIST_125MIN_START_COL = 10  # Column K (0-indexed)
WATCHLIST_HEADERS = ['Delete', 'Symbol', 'Sheet', 'Supertrend', 'Type', 'Pct Diff', 'Flatbase', 'Date Added']