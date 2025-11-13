"""
Instrument Mapper - Fetch and map trading symbols to instrument keys
"""

import requests
import gzip
import ijson
import pandas as pd
from typing import Dict, List
from config.settings import INSTRUMENT_FILTERS, API_CONFIG
from utils.logger import get_logger
from utils.validators import DataValidator

logger = get_logger(__name__)


class InstrumentMapper:
    """
    Fetch instrument data and create trading_symbol to instrument_key mapping
    """
    
    def __init__(self):
        """Initialize Instrument Mapper"""
        self.instruments_url = API_CONFIG['instruments_url']
        self.instrument_filters = INSTRUMENT_FILTERS
        self.instruments_df: pd.DataFrame = pd.DataFrame()
        self.instruments_dict: Dict[str, str] = {}
    
    def fetch_instruments(self) -> bool:
        """
        Fetch all instruments from Upstox and filter for equity stocks
        
        Returns:
            bool: True if successful
        """
        try:
            logger.info("Fetching instrument data from Upstox...")
            logger.info(f"URL: {self.instruments_url}")
            
            # Stream the gzipped JSON file
            resp = requests.get(self.instruments_url, stream=True, timeout=60)
            resp.raise_for_status()
            
            results = []
            count = 0
            
            # Process the gzipped JSON stream
            with gzip.GzipFile(fileobj=resp.raw) as gz:
                for item in ijson.items(gz, "item"):
                    count += 1
                    
                    # Filter for equity instruments
                    if (item['instrument_type'] in self.instrument_filters['instrument_types'] and
                        self.instrument_filters['key_pattern'] in item['instrument_key']):
                        
                        results.append({
                            'trading_symbol': item['trading_symbol'],
                            'instrument_key': item['instrument_key'],
                            'instrument_type': item['instrument_type'],
                            'name': item.get('name', ''),
                            'exchange': item.get('exchange', '')
                        })
                    
                    # Log progress every 10000 items
                    if count % 10000 == 0:
                        logger.info(f"Processed {count} instruments, found {len(results)} equity instruments")
            
            if not results:
                logger.error("No equity instruments found!")
                return False
            
            # Convert to DataFrame
            self.instruments_df = pd.DataFrame(results)
            
            logger.info(f"✓ Successfully fetched {len(self.instruments_df)} equity instruments")
            logger.info(f"  Total instruments processed: {count}")
            
            # Display sample
            logger.info("\nSample instruments:")
            logger.info(self.instruments_df.head(10).to_string(index=False))
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching instruments: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while fetching instruments: {e}")
            return False
    
    def create_mapping(self) -> Dict[str, str]:
        """
        Create mapping dictionary: {trading_symbol: instrument_key}
        Handles duplicates by keeping the most recent entry
        
        Returns:
            Dict[str, str]: Mapping of trading symbols to instrument keys
        """
        if self.instruments_df.empty:
            logger.error("No instruments data available. Call fetch_instruments() first.")
            return {}
        
        logger.info("Creating instrument mapping...")
        
        # Sort by trading_symbol and remove duplicates (keep last occurrence)
        df_unique = self.instruments_df.sort_values(by=['trading_symbol']).drop_duplicates(
            'trading_symbol',
            keep='last'
        )
        
        # Create the mapping dictionary
        self.instruments_dict = dict(zip(df_unique['trading_symbol'], df_unique['instrument_key']))
        
        logger.info(f"✓ Created mapping for {len(self.instruments_dict)} unique trading symbols")
        
        # Validate the mapping
        is_valid, message = DataValidator.validate_instrument_mapping(self.instruments_dict)
        if not is_valid:
            logger.error(f"Instrument mapping validation failed: {message}")
            return {}
        
        logger.info(f"✓ {message}")
        
        # Display sample mappings
        logger.info("\nSample instrument mappings:")
        for i, (symbol, key) in enumerate(list(self.instruments_dict.items())[:5]):
            logger.info(f"  {symbol} -> {key}")
        
        return self.instruments_dict
    
    def get_instruments(self) -> Dict[str, str]:
        """
        Get the instrument mapping dictionary
        
        Returns:
            Dict[str, str]: Mapping of trading symbols to instrument keys
        """
        return self.instruments_dict
    
    def get_instruments_list(self) -> List[str]:
        """
        Get list of all trading symbols
        
        Returns:
            List[str]: List of trading symbols
        """
        return list(self.instruments_dict.keys())
    
    def get_instrument_key(self, trading_symbol: str) -> str:
        """
        Get instrument key for a specific trading symbol
        
        Args:
            trading_symbol: The trading symbol to look up
        
        Returns:
            str: Instrument key or empty string if not found
        """
        return self.instruments_dict.get(trading_symbol, '')
    
    def save_mapping_to_csv(self, filename: str = 'instrument_mapping.csv') -> bool:
        """
        Save instrument mapping to CSV file for reference
        
        Args:
            filename: Output CSV filename
        
        Returns:
            bool: True if successful
        """
        try:
            if self.instruments_df.empty:
                logger.error("No instruments data to save")
                return False
            
            self.instruments_df.to_csv(filename, index=False)
            logger.info(f"✓ Instrument mapping saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving instrument mapping: {e}")
            return False
    
    def filter_by_symbols(self, symbols: List[str]) -> Dict[str, str]:
        """
        Filter mapping to only include specific symbols
        
        Args:
            symbols: List of trading symbols to include
        
        Returns:
            Dict[str, str]: Filtered mapping
        """
        filtered = {
            symbol: key for symbol, key in self.instruments_dict.items()
            if symbol in symbols
        }
        
        logger.info(f"Filtered to {len(filtered)} symbols from {len(symbols)} requested")
        
        missing = set(symbols) - set(filtered.keys())
        if missing:
            logger.warning(f"Symbols not found: {missing}")
        
        return filtered
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the instrument data
        
        Returns:
            Dict: Statistics dictionary
        """
        if self.instruments_df.empty:
            return {}
        
        stats = {
            'total_instruments': len(self.instruments_df),
            'unique_symbols': len(self.instruments_dict),
            'duplicates': len(self.instruments_df) - len(self.instruments_dict),
            'instrument_types': self.instruments_df['instrument_type'].value_counts().to_dict(),
            'exchanges': self.instruments_df['exchange'].value_counts().to_dict()
        }
        
        logger.info("\nInstrument Statistics:")
        logger.info(f"  Total instruments: {stats['total_instruments']}")
        logger.info(f"  Unique symbols: {stats['unique_symbols']}")
        logger.info(f"  Duplicates handled: {stats['duplicates']}")
        logger.info(f"  Instrument types: {stats['instrument_types']}")
        
        return stats
