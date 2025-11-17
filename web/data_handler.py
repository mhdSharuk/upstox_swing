"""
Data Handler for Google Sheets API operations
Handles fetching and processing data from Google Sheets
"""

import streamlit as st
import gspread
from google.oauth2 import service_account
import pandas as pd
from datetime import datetime
import config


def get_gspread_client():
    """Initialize and return gspread client with service account credentials"""
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    return gspread.authorize(credentials)


@st.cache_data(ttl=config.CACHE_TTL_SIGNALS, show_spinner=False)
def fetch_sheet_data(sheet_name):
    """
    Fetch all data from a specific sheet
    Returns: DataFrame with all data
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Get all values at once (faster than cell-by-cell)
        data = worksheet.get_all_values()
        
        if not data or len(data) < 2:
            return pd.DataFrame()
        
        # First row is headers
        headers = [str(h).strip().lower() for h in data[0]]
        rows = data[1:]
        
        # Create DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching {sheet_name}: {str(e)}")
        return pd.DataFrame()


def get_latest_rows_per_symbol(df):
    """
    Get the latest row for each symbol based on timestamp
    """
    if df.empty or 'trading_symbol' not in df.columns or 'timestamp' not in df.columns:
        return df
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # Sort by timestamp and get last occurrence of each symbol
    df_sorted = df.sort_values('timestamp')
    latest_df = df_sorted.groupby('trading_symbol').tail(1).reset_index(drop=True)
    
    return latest_df


def get_supertrend_columns(df, signal_type):
    """
    Extract available supertrend groups from column headers
    signal_type: 'daily' or '125min'
    """
    if df.empty:
        return []
    
    supertrends = []
    for col in df.columns:
        if col.startswith('pct_diff_latest_'):
            group_name = col.replace('pct_diff_latest_', '')
            
            if signal_type == '125min' and group_name in ['st_125m_sma15', 'st_125m_hl2']:
                supertrends.append(group_name)
            elif signal_type == 'daily' and group_name.startswith('st_daily_'):
                supertrends.append(group_name)
    
    return supertrends


def get_sectors(df):
    """Extract unique sectors from dataframe"""
    if df.empty or 'sector' not in df.columns:
        return ['All']
    
    sectors = df['sector'].dropna().unique().tolist()
    return ['All'] + sorted([s for s in sectors if s])


def get_industries(df):
    """Extract unique industries from dataframe"""
    if df.empty or 'industry' not in df.columns:
        return ['All']
    
    industries = df['industry'].dropna().unique().tolist()
    return ['All'] + sorted([i for i in industries if i])


def process_signals(df, supertrend, sector, industry, min_mcap, max_pct, min_flat):
    """
    Process and filter signals based on criteria
    Returns: (long_signals_df, short_signals_df)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get column names for selected supertrend
    pct_col = f'pct_diff_latest_{supertrend}'
    flat_col = f'flatbase_count_{supertrend}'
    dir_col = f'direction_{supertrend}'
    
    # Check if columns exist
    if pct_col not in df.columns or flat_col not in df.columns or dir_col not in df.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # Get latest rows per symbol
    latest_df = get_latest_rows_per_symbol(df)
    
    # Convert numeric columns
    latest_df['market_cap'] = pd.to_numeric(latest_df['market_cap'], errors='coerce')
    latest_df[pct_col] = pd.to_numeric(latest_df[pct_col], errors='coerce')
    latest_df[flat_col] = pd.to_numeric(latest_df[flat_col], errors='coerce')
    latest_df[dir_col] = pd.to_numeric(latest_df[dir_col], errors='coerce')
    latest_df['open'] = pd.to_numeric(latest_df['open'], errors='coerce')
    latest_df['close'] = pd.to_numeric(latest_df['close'], errors='coerce')
    
    # Apply filters
    filtered_df = latest_df.copy()
    
    # Sector filter
    if sector != 'All':
        filtered_df = filtered_df[filtered_df['sector'] == sector]
    
    # Industry filter
    if industry != 'All':
        filtered_df = filtered_df[filtered_df['industry'] == industry]
    
    # Market cap filter
    filtered_df = filtered_df[filtered_df['market_cap'] >= min_mcap]
    
    # Flatbase filter
    filtered_df = filtered_df[filtered_df[flat_col] >= min_flat]
    
    # Pct diff filter (absolute value)
    filtered_df = filtered_df[filtered_df[pct_col].abs() <= max_pct]
    
    # Calculate LTP percentage
    filtered_df['ltp'] = ((filtered_df['close'] - filtered_df['open']) / filtered_df['open'] * 100).round(2)
    
    # Prepare display columns
    filtered_df['pct_display'] = filtered_df[pct_col].round(2)
    filtered_df['flat_display'] = filtered_df[flat_col]
    filtered_df['close_display'] = filtered_df['close'].round(2)
    
    # Separate long and short signals
    long_signals = filtered_df[filtered_df[dir_col] == -1].copy()
    short_signals = filtered_df[filtered_df[dir_col] == 1].copy()
    
    # For short signals, use absolute pct value
    short_signals['pct_display'] = short_signals['pct_display'].abs()
    
    # Sort: by pct_diff ascending, then flatbase descending
    long_signals = long_signals.sort_values(['pct_display', 'flat_display'], ascending=[True, False])
    short_signals = short_signals.sort_values(['pct_display', 'flat_display'], ascending=[True, False])
    
    # Select and rename columns for display
    display_cols = {
        'trading_symbol': 'Symbol',
        'close_display': 'Close',
        'ltp': 'LTP %',
        'pct_display': 'Pct Diff',
        'flat_display': 'Flatbase'
    }
    
    long_signals_display = long_signals[list(display_cols.keys())].rename(columns=display_cols).reset_index(drop=True)
    short_signals_display = short_signals[list(display_cols.keys())].rename(columns=display_cols).reset_index(drop=True)
    
    # Add supertrend info for watchlist operations
    long_signals_display['_supertrend'] = supertrend
    short_signals_display['_supertrend'] = supertrend
    
    return long_signals_display, short_signals_display


@st.cache_data(ttl=config.CACHE_TTL_WATCHLIST, show_spinner=False)
def fetch_watchlist_data():
    """
    Fetch watchlist data from Google Sheets
    Returns: List of dictionaries with watchlist items
    """
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(config.WATCHLIST_SHEET)
        except gspread.exceptions.WorksheetNotFound:
            # Watchlist sheet doesn't exist yet
            return []
        
        # Get all values
        data = worksheet.get_all_values()
        
        if len(data) < 4:  # Headers start at row 3 (index 2), data at row 4 (index 3)
            return []
        
        watchlist = []
        
        # Daily watchlist (columns A-H, starting row 4)
        for i in range(3, len(data)):
            if data[i][1]:  # Check if Symbol column (B) has value
                watchlist.append({
                    'symbol': data[i][1],
                    'sheet': data[i][2],
                    'supertrend': data[i][3],
                    'type': data[i][4],
                    'pct': data[i][5],
                    'flatbase': data[i][6],
                    'date_added': data[i][7] if len(data[i]) > 7 else ''
                })
        
        # 125min watchlist (columns K-R, starting row 4)
        for i in range(3, len(data)):
            if len(data[i]) > 11 and data[i][11]:  # Check if Symbol column (L) has value
                watchlist.append({
                    'symbol': data[i][11],
                    'sheet': data[i][12],
                    'supertrend': data[i][13],
                    'type': data[i][14],
                    'pct': data[i][15],
                    'flatbase': data[i][16],
                    'date_added': data[i][17] if len(data[i]) > 17 else ''
                })
        
        return watchlist
        
    except Exception as e:
        st.error(f"Error fetching watchlist: {str(e)}")
        return []


def clear_cache():
    """Clear all cached data"""
    st.cache_data.clear()


def clear_watchlist_cache_only():
    """Clear only watchlist cache, keep signal data cached"""
    # This will only clear the watchlist cache while preserving signal data cache
    fetch_watchlist_data.clear()