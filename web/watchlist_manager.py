"""
Watchlist Manager - Handles add/remove operations for watchlist
"""

import streamlit as st
import gspread
from datetime import datetime
import config
from data_handler import get_gspread_client


def create_watchlist_sheet_if_not_exists():
    """Create watchlist sheet with proper structure if it doesn't exist"""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        
        try:
            worksheet = spreadsheet.worksheet(config.WATCHLIST_SHEET)
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            # Create new sheet
            worksheet = spreadsheet.add_worksheet(title=config.WATCHLIST_SHEET, rows=100, cols=20)
            
            # Set up headers and structure
            # Row 1: Daily Watchlist title (merged A1:H1)
            worksheet.update('A1', [['Daily Watchlist']])
            worksheet.format('A1:H1', {
                'horizontalAlignment': 'CENTER',
                'backgroundColor': {'red': 0.91, 'green': 0.94, 'blue': 0.99},
                'textFormat': {'fontSize': 12, 'fontFamily': 'Roboto'}
            })
            worksheet.merge_cells('A1:H1')
            
            # Row 1: 125min Watchlist title (merged K1:R1)
            worksheet.update('K1', [['125min Watchlist']])
            worksheet.format('K1:R1', {
                'horizontalAlignment': 'CENTER',
                'backgroundColor': {'red': 0.91, 'green': 0.94, 'blue': 0.99},
                'textFormat': {'fontSize': 12, 'fontFamily': 'Roboto'}
            })
            worksheet.merge_cells('K1:R1')
            
            # Row 3: Daily headers
            worksheet.update('A3:H3', [config.WATCHLIST_HEADERS])
            worksheet.format('A3:H3', {
                'backgroundColor': {'red': 0.29, 'green': 0.53, 'blue': 0.91},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'fontSize': 10, 'fontFamily': 'Roboto'},
                'horizontalAlignment': 'LEFT',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Row 3: 125min headers
            worksheet.update('K3:R3', [config.WATCHLIST_HEADERS])
            worksheet.format('K3:R3', {
                'backgroundColor': {'red': 0.29, 'green': 0.53, 'blue': 0.91},
                'textFormat': {'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}, 'fontSize': 10, 'fontFamily': 'Roboto'},
                'horizontalAlignment': 'LEFT',
                'verticalAlignment': 'MIDDLE'
            })
            
            # Freeze first 3 rows
            worksheet.freeze(rows=3)
            
            return worksheet
            
    except Exception as e:
        st.error(f"Error creating watchlist sheet: {str(e)}")
        return None


def is_in_watchlist(symbol, sheet, supertrend, signal_type, watchlist_data):
    """Check if item is in watchlist"""
    for item in watchlist_data:
        if (item['symbol'] == symbol and 
            item['sheet'] == sheet and 
            item['supertrend'] == supertrend and 
            item['type'] == signal_type):
            return True
    return False


def add_to_watchlist(symbol, sheet, supertrend, signal_type, pct, flatbase):
    """Add item to watchlist"""
    try:
        # Convert to native Python types to avoid JSON serialization issues
        pct = float(pct) if pct is not None else 0.0
        flatbase = int(flatbase) if flatbase is not None else 0
        
        worksheet = create_watchlist_sheet_if_not_exists()
        if not worksheet:
            return False
        
        # Determine which column to use based on sheet
        if sheet == 'daily_signals':
            start_col = config.WATCHLIST_DAILY_START_COL + 1  # Convert to 1-indexed
            col_letter = 'A'
        else:  # 125min_signals
            start_col = config.WATCHLIST_125MIN_START_COL + 1  # Convert to 1-indexed
            col_letter = 'K'
        
        # Find next empty row (starting from row 4)
        all_values = worksheet.get_all_values()
        next_row = 4
        
        for i in range(3, len(all_values)):
            if sheet == 'daily_signals':
                if not all_values[i][1]:  # Column B (Symbol) is empty
                    next_row = i + 1
                    break
            else:
                if len(all_values[i]) > 11 and not all_values[i][11]:  # Column L (Symbol) is empty
                    next_row = i + 1
                    break
        else:
            next_row = len(all_values) + 1
        
        # Prepare row data
        date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row_data = [True, symbol, sheet, supertrend, signal_type, pct, flatbase, date_added]
        
        # Update the row
        range_name = f'{col_letter}{next_row}:{chr(ord(col_letter) + 7)}{next_row}'
        worksheet.update(range_name, [row_data])
        
        # Format checkbox in first column
        checkbox_range = f'{col_letter}{next_row}'
        worksheet.update(checkbox_range, [[True]], value_input_option='USER_ENTERED')
        
        return True
        
    except Exception as e:
        st.error(f"Error adding to watchlist: {str(e)}")
        return False


def remove_from_watchlist(symbol, sheet, supertrend, signal_type):
    """Remove item from watchlist"""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(config.WATCHLIST_SHEET)
        
        # Determine which columns to check based on sheet
        if sheet == 'daily_signals':
            symbol_col = 2  # Column B (1-indexed)
            sheet_col = 3   # Column C
            st_col = 4      # Column D
            type_col = 5    # Column E
        else:  # 125min_signals
            symbol_col = 12  # Column L (1-indexed)
            sheet_col = 13   # Column M
            st_col = 14      # Column N
            type_col = 15    # Column O
        
        # Get all values
        all_values = worksheet.get_all_values()
        
        # Find the row to delete (starting from row 4)
        for i in range(3, len(all_values)):
            row = all_values[i]
            
            if len(row) >= max(symbol_col, sheet_col, st_col, type_col):
                if (row[symbol_col - 1] == symbol and 
                    row[sheet_col - 1] == sheet and 
                    row[st_col - 1] == supertrend and 
                    row[type_col - 1] == signal_type):
                    
                    # Delete the row
                    worksheet.delete_rows(i + 1)  # gspread uses 1-indexed rows
                    return True
        
        return False
        
    except Exception as e:
        st.error(f"Error removing from watchlist: {str(e)}")
        return False


def get_watchlist_as_dataframe(watchlist_data):
    """Convert watchlist data to pandas DataFrame for display"""
    import pandas as pd
    
    if not watchlist_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(watchlist_data)
    df = df.rename(columns={
        'symbol': 'Symbol',
        'sheet': 'Sheet',
        'supertrend': 'Supertrend',
        'type': 'Type',
        'pct': 'Pct Diff',
        'flatbase': 'Flatbase',
        'date_added': 'Date Added'
    })
    
    return df