# Upstox Supertrend Project

A comprehensive Python application to fetch market data from Upstox, calculate custom supertrend indicators across multiple timeframes, detect flat base patterns, and save results to Google Sheets.

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- **Upstox API Integration**
  - Automatic token management and validation
  - OAuth2 authentication flow with TOTP
  - Asynchronous data fetching for efficiency

- **Market Data Fetching**
  - Fetch all NSE equity instrument keys
  - Historical data for multiple timeframes (125-minute and daily)
  - Smart date range selection based on Upstox API limits

- **Technical Indicators**
  - Custom supertrend calculations (translated from Pine Script)
  - Support for SMA-based and HL2-based variations
  - Multiple parameter configurations per timeframe
  - State preservation for incremental calculations

- **Flat Base Detection**
  - Detect periods where supertrend values remain stable
  - Configurable tolerance (0.1% by default)
  - Count consecutive flat base periods

- **Google Sheets Integration**
  - Batch upload with rate limit handling
  - Automatic sheet creation and management
  - Data retention limits (latest N candles per symbol)

## 📁 Project Structure

```
upstox_supertrend_project/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Project configuration
│   └── credentials.py       # API keys and secrets (user fills)
├── auth/
│   ├── __init__.py
│   ├── token_manager.py     # Token validation and management
│   └── upstox_auth.py       # OAuth2 authentication
├── data_fetcher/
│   ├── __init__.py
│   ├── instrument_mapper.py # Fetch and map instruments
│   └── historical_data.py   # Async historical data fetching
├── indicators/
│   ├── __init__.py
│   ├── atr.py              # ATR calculation
│   ├── supertrend.py       # Supertrend indicator (Pine Script → Python)
│   └── flat_base.py        # Flat base pattern detection
├── storage/
│   ├── __init__.py
│   └── sheets_writer.py    # Google Sheets writer
├── utils/
│   ├── __init__.py
│   ├── logger.py           # Logging utilities
│   └── validators.py       # Data validation
├── existing_files/         # Reference files
│   ├── upstox_login.py
│   ├── upstox_data_fetcher.py
│   └── upstox_token.json
├── main.py                 # Main orchestration script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🔧 Requirements

- Python 3.8 or higher
- Upstox Trading Account
- Google Cloud Service Account (for Sheets API)
- Active internet connection

## 📦 Installation

### 1. Clone or Download the Project

```bash
cd upstox_supertrend_project
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

### 1. Upstox API Credentials

1. Go to [Upstox Developer Portal](https://upstox.com/developer/apps/)
2. Create a new app or use existing one
3. Note down:
   - API Key
   - API Secret
   - Redirect URI (use `http://127.0.0.1:8000/callback`)
   - TOTP Secret (from your 2FA setup)

### 2. Google Sheets Setup

1. Create a new Google Cloud Project
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account
4. Download the service account JSON key file
5. Create a new Google Sheet and share it with the service account email
6. Note the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`

### 3. Update Configuration Files

Edit `config/credentials.py`:

```python
# Upstox API credentials
UPSTOX_API_KEY = "your_api_key_here"
UPSTOX_API_SECRET = "your_api_secret_here"
UPSTOX_REDIRECT_URI = "http://127.0.0.1:8000/callback"
UPSTOX_TOTP_SECRET = "your_totp_secret_here"

# Google Sheets credentials
GOOGLE_SHEET_ID = "your_google_sheet_id_here"
SERVICE_ACCOUNT_FILE = "service_account.json"  # Path to your JSON key file
```

### 4. Place Service Account File

Copy your Google service account JSON file to the project root:

```bash
cp /path/to/your/service-account.json service_account.json
```

## 🚀 Usage

### Run the Complete Pipeline

```bash
python main.py
```

The pipeline will:

1. **Authenticate** with Upstox (validates existing token or runs login flow)
2. **Fetch Instruments** (all NSE equity stocks)
3. **Fetch Historical Data** (125-minute and daily candles)
4. **Calculate Supertrends** (2 types for 125min, 4 types for daily)
5. **Detect Flat Bases** (0.1% tolerance)
6. **Save to Google Sheets** (with data retention limits)

### First-Time Authentication

On first run or when token expires:
1. Browser will open automatically
2. Enter your Upstox credentials
3. Use the displayed TOTP code for 2FA
4. Click "Authorize"
5. Token is saved and will be reused until expiry (3:30 AM IST)

### Subsequent Runs

The script will:
- Validate existing token
- Reuse token if valid
- Automatically re-authenticate if expired

## 🔬 Technical Details

### Supertrend Configurations

#### 125-Minute Timeframe (2 configurations)

| Name | Source | ATR Period | Multiplier | Description |
|------|--------|------------|------------|-------------|
| ST_125m_sma15 | SMA(HL2, 15) | 15 | 2.0 | Weekly reference with SMA |
| ST_125m_hl2 | HL2 | 15 | 2.0 | Weekly reference without SMA |

#### Daily Timeframe (4 configurations)

| Name | Source | ATR Period | Multiplier | Description |
|------|--------|------------|------------|-------------|
| ST_daily_sma7 | SMA(HL2, 7) | 7 | 2.0 | Weekly reference with SMA |
| ST_daily_sma20 | SMA(HL2, 20) | 20 | 2.0 | Monthly reference with SMA |
| ST_daily_hl2_20 | HL2 | 20 | 2.0 | Monthly reference without SMA |
| ST_daily_hl2_7 | HL2 | 7 | 2.0 | Weekly reference without SMA |

### Flat Base Detection

- **Tolerance**: Exactly 0.1% (0.001)
- **Formula**: `abs(ST[i] - ST[i-1]) / ST[i-1] <= 0.001`
- **Counting**: Starts at 2 for consecutive flat bases
- **Reset**: Counter resets to 1 when tolerance is broken

### Data Retention

- **125-minute**: Latest 200 candles per symbol
- **Daily**: Latest 60 candles per symbol

### State Variables for Incremental Calculation

For each supertrend configuration, the following state is preserved:
- `prev_supertrend`: Last supertrend value
- `prev_upperBand`: Last upper band value
- `prev_lowerBand`: Last lower band value
- `prev_direction`: Last direction (-1 or 1)
- `prev_hl2`: Last HL2 value
- `prev_close`: Last close price

This enables O(1) time complexity for future updates when new candles arrive.

## 📊 Output

### Google Sheets Structure

#### Sheet: "125min_data"

Columns:
- trading_symbol
- timestamp
- open, high, low, close, hl2
- supertrend_ST_125m_sma15, direction_ST_125m_sma15, flatbase_count_ST_125m_sma15
- supertrend_ST_125m_hl2, direction_ST_125m_hl2, flatbase_count_ST_125m_hl2

#### Sheet: "daily_data"

Columns:
- trading_symbol
- timestamp
- open, high, low, close, hl2
- supertrend_ST_daily_sma7, direction_ST_daily_sma7, flatbase_count_ST_daily_sma7
- supertrend_ST_daily_sma20, direction_ST_daily_sma20, flatbase_count_ST_daily_sma20
- supertrend_ST_daily_hl2_20, direction_ST_daily_hl2_20, flatbase_count_ST_daily_hl2_20
- supertrend_ST_daily_hl2_7, direction_ST_daily_hl2_7, flatbase_count_ST_daily_hl2_7

## 🐛 Troubleshooting

### Authentication Issues

**Problem**: Token expired or authentication fails

**Solution**:
1. Delete `upstox_token.json`
2. Run the script again
3. Complete the login flow in browser

### Rate Limit Errors

**Problem**: Too many API requests

**Solution**:
- The script includes automatic retry logic
- Reduce `max_concurrent_requests` in `config/settings.py`
- Add delays between batches

### Google Sheets Authentication Error

**Problem**: Cannot authenticate with Google Sheets

**Solution**:
1. Verify `service_account.json` is in project root
2. Ensure the service account email has access to your sheet
3. Check that Google Sheets API is enabled in your Google Cloud project

### No Data Fetched

**Problem**: Some instruments return no data

**Solution**:
- This is normal for stocks with no recent trading
- The script continues processing other instruments
- Check logs for specific error messages

### Memory Issues

**Problem**: Script uses too much memory

**Solution**:
- Process fewer instruments at once
- Modify `ASYNC_CONFIG` in `config/settings.py`
- Reduce chunk sizes

## 📝 Logging

Logs are written to:
- Console (stdout)
- File: `upstox_supertrend.log`

Log levels can be adjusted in `config/settings.py`:
```python
LOGGING_CONFIG = {
    'level': 'INFO',  # Change to 'DEBUG' for more verbose output
    ...
}
```

## 🔐 Security Notes

- Never commit `credentials.py` with actual credentials
- Add `credentials.py` to `.gitignore`
- Keep `service_account.json` secure
- Tokens expire at 3:30 AM IST daily

## 📄 License

This project is for personal use. Ensure compliance with Upstox and Google's terms of service.

## 🤝 Support

For issues:
1. Check the troubleshooting section
2. Review logs in `upstox_supertrend.log`
3. Verify all credentials are correct
4. Ensure all dependencies are installed

## 📚 References

- [Upstox API Documentation](https://upstox.com/developer/api-documentation)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Pine Script Documentation](https://www.tradingview.com/pine-script-docs/)

---

**Note**: This is a one-time batch operation. For real-time updates, a different approach using websockets would be more appropriate.
