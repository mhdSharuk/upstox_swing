"""
Utility functions for Signal Tracker
"""

from datetime import datetime
import pytz


def is_market_hours():
    """
    Check if current time is within market hours (IST timezone)
    Market hours: 9:15 AM - 3:30 PM IST
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now.weekday() > 4:  # Saturday or Sunday
        return False
    
    current_time = now.time()
    market_start = datetime.strptime("09:15", "%H:%M").time()
    market_end = datetime.strptime("15:30", "%H:%M").time()
    
    return market_start <= current_time <= market_end


def format_number(value, decimals=2):
    """Format number with specified decimal places"""
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return value


def get_current_timestamp():
    """Get current timestamp as formatted string"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def format_percentage(value, decimals=2):
    """Format value as percentage"""
    try:
        return f"{round(float(value), decimals)}%"
    except (ValueError, TypeError):
        return str(value)


def safe_float_convert(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int_convert(value, default=0):
    """Safely convert value to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default