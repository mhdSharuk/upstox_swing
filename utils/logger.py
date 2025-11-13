"""
Logging utility for Upstox Supertrend Project
FIXED VERSION: Handles UTF-8 encoding on Windows
"""

import logging
import sys
from typing import Optional
from config.settings import LOGGING_CONFIG


# Global logger cache
_loggers = {}


def setup_logging(
    level: str = LOGGING_CONFIG['level'],
    log_file: Optional[str] = LOGGING_CONFIG['file'],
    console: bool = LOGGING_CONFIG['console']
) -> None:
    """
    Setup logging configuration for the entire application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for no file logging)
        console: Whether to log to console
    """
    log_format = LOGGING_CONFIG['format']
    log_level = getattr(logging, level.upper())
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler with UTF-8 encoding support
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        # Force UTF-8 encoding on Windows to handle Unicode characters
        if sys.platform.startswith('win'):
            try:
                # Python 3.7+ has reconfigure method
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8')
                # Fallback for older versions
                elif hasattr(sys.stdout, 'buffer'):
                    import io
                    sys.stdout = io.TextIOWrapper(
                        sys.stdout.buffer,
                        encoding='utf-8',
                        errors='replace'
                    )
            except Exception as e:
                # If UTF-8 configuration fails, continue with default encoding
                print(f"Warning: Could not set UTF-8 encoding: {e}")
                print("Unicode characters may not display correctly")
        
        root_logger.addHandler(console_handler)
    
    # File handler with explicit UTF-8 encoding
    if log_file:
        try:
            file_handler = logging.FileHandler(
                log_file,
                mode='a',
                encoding='utf-8'  # Force UTF-8 for file
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name
    
    Args:
        name: Name of the logger (typically __name__ of the module)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger
    
    return _loggers[name]


class ProgressLogger:
    """
    Helper class for logging progress during long operations
    """
    
    def __init__(self, total: int, operation: str, logger: logging.Logger):
        """
        Initialize progress logger
        
        Args:
            total: Total number of items to process
            operation: Description of the operation
            logger: Logger instance to use
        """
        self.total = total
        self.operation = operation
        self.logger = logger
        self.current = 0
        self.last_percentage = -1
    
    def update(self, increment: int = 1) -> None:
        """
        Update progress
        
        Args:
            increment: Number of items processed
        """
        self.current += increment
        percentage = int((self.current / self.total) * 100)
        
        # Log every 10% or at completion
        if percentage >= self.last_percentage + 10 or self.current == self.total:
            self.logger.info(
                f"{self.operation}: {self.current}/{self.total} ({percentage}%)"
            )
            self.last_percentage = percentage
    
    def complete(self, message: Optional[str] = None) -> None:
        """
        Mark operation as complete
        
        Args:
            message: Optional completion message
        """
        if message:
            self.logger.info(f"[OK] {self.operation} completed: {message}")
        else:
            self.logger.info(f"[OK] {self.operation} completed: {self.current}/{self.total}")


# Safe Unicode symbols for logging
# These will work if UTF-8 is configured, otherwise will be replaced
def safe_symbol(unicode_char: str, ascii_fallback: str) -> str:
    """
    Return unicode character if encoding supports it, otherwise ASCII fallback
    
    Args:
        unicode_char: Unicode character (e.g., '✓')
        ascii_fallback: ASCII alternative (e.g., '[OK]')
    
    Returns:
        Safe character for current encoding
    """
    try:
        # Test if current stdout can encode the character
        encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
        unicode_char.encode(encoding)
        return unicode_char
    except (UnicodeEncodeError, AttributeError, LookupError):
        return ascii_fallback


# Export safe symbols for use throughout the application
CHECK = safe_symbol('✓', '[OK]')
CROSS = safe_symbol('✗', '[X]')
WARNING = safe_symbol('⚠', '[!]')
ARROW = safe_symbol('→', '->')
INFO = safe_symbol('ℹ', '[i]')
STAR = safe_symbol('⭐', '*')