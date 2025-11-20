"""
Instrument Mapper - HYBRID VERSION
Tries Upstox directly first, automatically falls back to Supabase if blocked
Works on both local machines and PythonAnywhere (free or paid accounts)

This version is smart:
- FREE PythonAnywhere: Uses Supabase (Upstox blocked)
- PAID PythonAnywhere: Uses Upstox directly (faster)
- LOCAL machine: Uses Upstox directly (faster)
"""

import requests
import gzip
import ijson
import json
import pandas as pd
from typing import Dict, List, Optional, Set, Tuple
from config.settings import INSTRUMENT_FILTERS, API_CONFIG
from config.env_loader import SUPABASE_URL
from utils.logger import get_logger
from utils.validators import DataValidator

logger = get_logger(__name__)


class InstrumentMapper:
    """
    Fetch instrument data and create trading_symbol to instrument_key mapping
    HYBRID: Automatically chooses best source (Upstox or Supabase)
    """
    
    def __init__(self, access_token: str):
        """
        Initialize Instrument Mapper
        
        Args:
            access_token: Upstox API access token
        """
        self.access_token = access_token
        self.upstox_url = API_CONFIG['instruments_url']
        self.supabase_url = f"{SUPABASE_URL}/storage/v1/object/public/st-swing-bucket/data/instruments_complete.json.gz"
        self.instrument_filters = INSTRUMENT_FILTERS
        self.instruments_df: pd.DataFrame = pd.DataFrame()
        self.instruments_dict: Dict[str, str] = {}
        self.source_used: str = "unknown"  # Track which source was used
    
    def _fetch_from_upstox(self, allowed_symbols: Optional[Set[str]] = None) -> Tuple[bool, List[Dict]]:
        """
        Try to fetch instruments from Upstox directly
        
        Args:
            allowed_symbols: Optional set of symbols to include
        
        Returns:
            Tuple[bool, List[Dict]]: (success, results_list)
        """
        logger.info("Attempting to fetch from Upstox (direct)...")
        logger.info(f"  URL: {self.upstox_url}")
        
        try:
            # Make request with short timeout to fail fast if blocked
            resp = requests.get(self.upstox_url, stream=True, timeout=15)
            resp.raise_for_status()
            
            logger.info("  ✓ Connected to Upstox successfully")
            
            # Process the gzipped JSON stream
            results = []
            count = 0
            
            with gzip.GzipFile(fileobj=resp.raw) as gz:
                for item in ijson.items(gz, "item"):
                    count += 1
                    
                    # Filter for equity instruments
                    if (item['instrument_type'] in self.instrument_filters['instrument_types'] and
                        self.instrument_filters['key_pattern'] in item['instrument_key']):
                        
                        trading_symbol = item['trading_symbol']
                        
                        # If allowed_symbols is provided, only include symbols in that set
                        if allowed_symbols and trading_symbol not in allowed_symbols:
                            continue
                        
                        results.append({
                            'trading_symbol': trading_symbol,
                            'instrument_key': item['instrument_key'],
                            'instrument_type': item['instrument_type'],
                            'name': item.get('name', ''),
                            'exchange': item.get('exchange', '')
                        })
                    
                    # Log progress every 10000 items
                    if count % 10000 == 0:
                        logger.info(f"  Processed {count} instruments, found {len(results)} equity instruments")
            
            logger.info(f"  ✓ Successfully fetched from Upstox")
            logger.info(f"  Total processed: {count}, Equity found: {len(results)}")
            
            if not results:
                logger.warning("  ⚠ No equity instruments found in Upstox data")
                return False, []
            
            self.source_used = "Upstox (direct)"
            return True, results
            
        except requests.exceptions.ProxyError as e:
            logger.warning("  ✗ Upstox blocked by proxy (403 Forbidden)")
            logger.info("  → This is normal on PythonAnywhere free accounts")
            return False, []
        
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"  ✗ Connection error: {str(e)[:100]}")
            logger.info("  → Upstox URL may be blocked")
            return False, []
        
        except requests.exceptions.Timeout:
            logger.warning("  ✗ Request timed out")
            logger.info("  → Upstox may be slow or blocked")
            return False, []
        
        except Exception as e:
            logger.warning(f"  ✗ Upstox fetch failed: {str(e)[:100]}")
            return False, []
    
    def _fetch_from_supabase(self, allowed_symbols: Optional[Set[str]] = None) -> Tuple[bool, List[Dict]]:
        """
        Fetch instruments from Supabase Storage (fallback)
        
        Args:
            allowed_symbols: Optional set of symbols to include
        
        Returns:
            Tuple[bool, List[Dict]]: (success, results_list)
        """
        logger.info("Attempting to fetch from Supabase Storage (fallback)...")
        logger.info(f"  URL: {self.supabase_url}")
        
        try:
            # Fetch from Supabase
            response = requests.get(self.supabase_url, timeout=30)
            response.raise_for_status()
            
            file_size_mb = len(response.content) / (1024 * 1024)
            logger.info(f"  ✓ Downloaded {file_size_mb:.2f} MB from Supabase")
            
            # Decompress and parse
            decompressed = gzip.decompress(response.content)
            data = json.loads(decompressed)
            
            logger.info(f"  ✓ Parsed {len(data)} total instruments")
            
            # Filter for equity instruments
            results = []
            
            for item in data:
                if (item.get('instrument_type') in self.instrument_filters['instrument_types'] and
                    self.instrument_filters['key_pattern'] in item.get('instrument_key', '')):
                    
                    trading_symbol = item.get('trading_symbol')
                    
                    if allowed_symbols and trading_symbol not in allowed_symbols:
                        continue
                    
                    results.append({
                        'trading_symbol': trading_symbol,
                        'instrument_key': item.get('instrument_key'),
                        'instrument_type': item.get('instrument_type'),
                        'name': item.get('name', ''),
                        'exchange': item.get('exchange', '')
                    })
            
            logger.info(f"  ✓ Found {len(results)} equity instruments")
            
            if not results:
                logger.error("  ✗ No equity instruments found after filtering")
                return False, []
            
            self.source_used = "Supabase Storage (fallback)"
            return True, results
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"  ✗ HTTP error: {e}")
            logger.error(f"  Status: {response.status_code}")
            
            if response.status_code == 404:
                logger.error("\n  ⚠ INSTRUMENTS FILE NOT FOUND IN SUPABASE!")
                logger.error("  → Run this on your LOCAL machine:")
                logger.error("     python3 scripts/update_instruments_to_supabase.py")
                logger.error("  → This will download from Upstox and upload to Supabase")
            
            return False, []
        
        except Exception as e:
            logger.error(f"  ✗ Supabase fetch failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, []
    
    def fetch_instruments(self, allowed_symbols: Optional[Set[str]] = None) -> bool:
        """
        Fetch all instruments with automatic fallback
        Tries Upstox first, falls back to Supabase if blocked
        
        Args:
            allowed_symbols: Optional set of symbols to include (for market cap filtering)
        
        Returns:
            bool: True if successful from either source
        """
        logger.info("=" * 60)
        logger.info("FETCHING INSTRUMENTS (HYBRID MODE)")
        logger.info("=" * 60)
        
        if allowed_symbols:
            logger.info(f"Filtering for {len(allowed_symbols)} symbols with market cap >= {self.instrument_filters['min_market_cap']} Cr")
        
        # Try Upstox first
        success, results = self._fetch_from_upstox(allowed_symbols)
        
        # If Upstox failed, try Supabase
        if not success:
            logger.info("\n" + "─" * 60)
            logger.info("Upstox unavailable, trying Supabase fallback...")
            logger.info("─" * 60)
            
            success, results = self._fetch_from_supabase(allowed_symbols)
            
            if not success:
                logger.error("\n" + "=" * 60)
                logger.error("✗ BOTH SOURCES FAILED")
                logger.error("=" * 60)
                logger.error("Neither Upstox nor Supabase Storage is accessible")
                logger.error("\nPossible solutions:")
                logger.error("1. Check internet connection")
                logger.error("2. Upload instruments to Supabase:")
                logger.error("   python3 scripts/update_instruments_to_supabase.py")
                logger.error("3. Check Supabase bucket: st-swing-bucket/data/")
                return False
        
        # Convert to DataFrame
        try:
            self.instruments_df = pd.DataFrame(results)
            logger.info(f"\n✓ Created DataFrame with {len(self.instruments_df)} rows")
            logger.info(f"✓ Data source: {self.source_used}")
            
        except Exception as e:
            logger.error(f"✗ Error creating DataFrame: {e}")
            return False
        
        logger.info("=" * 60)
        logger.info("✓ INSTRUMENT FETCH SUCCESSFUL")
        logger.info("=" * 60)
        
        return True
    
    def create_mapping(self) -> Dict[str, str]:
        """
        Create mapping dictionary: {trading_symbol: instrument_key}
        Handles duplicates by keeping the most recent entry
        
        Returns:
            Dict[str, str]: Mapping of trading symbols to instrument keys
        """
        if self.instruments_df.empty:
            logger.error("✗ No instruments data available. Call fetch_instruments() first.")
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
    
    def create_instrument_mapping(self, allowed_symbols: Optional[Set[str]] = None) -> Dict[str, str]:
        """
        Complete process: fetch and create mapping
        
        Args:
            allowed_symbols: Optional set of symbols to include (for market cap filtering)
        
        Returns:
            Dict[str, str]: Instrument mapping dictionary
        """
        if not self.fetch_instruments(allowed_symbols):
            return {}
        
        return self.create_mapping()
    
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
    
    def get_source_used(self) -> str:
        """
        Get the data source that was actually used
        
        Returns:
            str: "Upstox (direct)" or "Supabase Storage (fallback)"
        """
        return self.source_used
    
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
            'exchanges': self.instruments_df['exchange'].value_counts().to_dict(),
            'source': self.source_used
        }
        
        logger.info("\nInstrument Statistics:")
        logger.info(f"  Total instruments: {stats['total_instruments']}")
        logger.info(f"  Unique symbols: {stats['unique_symbols']}")
        logger.info(f"  Duplicates handled: {stats['duplicates']}")
        logger.info(f"  Data source: {stats['source']}")
        
        return stats