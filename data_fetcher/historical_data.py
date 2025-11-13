"""
Historical Data Fetcher - Asynchronously fetch historical candle data from Upstox
FIXED VERSION: Uses asyncio.gather() and handles Unicode encoding
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config.settings import API_CONFIG, TIMEFRAME_CONFIG, ASYNC_CONFIG
from utils.logger import get_logger, ProgressLogger
from utils.validators import DataValidator

logger = get_logger(__name__)


class HistoricalDataFetcher:
    def __init__(self, access_token: str):
        """
        Initialize Historical Data Fetcher
        
        Args:
            access_token: Upstox API access token
        """
        self.access_token = access_token
        self.base_url = API_CONFIG['base_url'] + API_CONFIG['historical_endpoint']
        self.rate_limit_delay = API_CONFIG['rate_limit_delay']
        self.max_retries = API_CONFIG['max_retries']
        self.retry_delay = API_CONFIG['retry_delay']
        self.max_concurrent = ASYNC_CONFIG['max_concurrent_requests']
    
    def _get_date_range(self, timeframe: str) -> Tuple[str, str]:
        to_date = datetime.now()
        to_date_str = to_date.strftime('%Y-%m-%d')
        
        config = TIMEFRAME_CONFIG.get(timeframe, {})
        days_history = config.get('days_history', 90)
        
        from_date = to_date - timedelta(days=days_history)
        from_date_str = from_date.strftime('%Y-%m-%d')
        
        return from_date_str, to_date_str
    
    async def fetch_candle_data(self,session: aiohttp.ClientSession,instrument_key: str,
                                trading_symbol: str,timeframe: str,
                                semaphore: asyncio.Semaphore) -> Optional[pd.DataFrame]:
        async with semaphore:
            config = TIMEFRAME_CONFIG.get(timeframe, {})
            unit = config['unit']
            interval = config['interval']
            
            from_date, to_date = self._get_date_range(timeframe)
            
            # Construct URL
            url = f"{self.base_url}/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            for attempt in range(self.max_retries):
                try:
                    # Add delay to respect rate limits
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("status") != "success":
                                logger.warning(
                                    f"{trading_symbol}: API returned non-success status"
                                )
                                return None
                            
                            candles = data.get("data", {}).get("candles", [])
                            
                            if not candles:
                                logger.debug(f"{trading_symbol}: No candle data available")
                                return None
                            
                            # Convert to DataFrame
                            df = pd.DataFrame(candles, columns=[
                                "timestamp", "open", "high", "low", "close", "volume", "open_interest"
                            ])
                            
                            # Convert timestamp to datetime
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            
                            # Add trading symbol
                            df['trading_symbol'] = trading_symbol
                            
                            # Calculate HL2
                            df['hl2'] = (df['high'] + df['low']) / 2
                            
                            # Sort by timestamp (oldest first)
                            df = df.sort_values('timestamp').reset_index(drop=True)
                            
                            # Validate data
                            is_valid, message = DataValidator.validate_candle_data(df)
                            if not is_valid:
                                logger.warning(f"{trading_symbol}: Data validation failed - {message}")
                                return None
                            
                            return df
                        
                        elif response.status == 429:
                            # Rate limit hit
                            wait_time = self.retry_delay * (attempt + 1)
                            logger.warning(
                                f"{trading_symbol}: Rate limit hit, waiting {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        
                        elif response.status == 401:
                            logger.error(f"{trading_symbol}: Authentication error - token may be expired")
                            return None
                        
                        else:
                            logger.warning(
                                f"{trading_symbol}: HTTP {response.status}, attempt {attempt + 1}/{self.max_retries}"
                            )
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay)
                                continue
                            return None
                
                except asyncio.TimeoutError:
                    logger.warning(f"{trading_symbol}: Timeout, attempt {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return None
                
                except Exception as e:
                    logger.error(f"{trading_symbol}: Error fetching data - {e}")
                    return None
            
            return None
    
    async def fetch_multiple_instruments(self,instruments: Dict[str, str],timeframe: str) -> Dict[str, pd.DataFrame]:
        
        logger.info(f"Fetching {timeframe} data for {len(instruments)} instruments...")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = {}
        
        async with aiohttp.ClientSession() as session:
            # Create all tasks upfront for concurrent execution
            tasks = [
                self.fetch_candle_data(
                    session,
                    instrument_key,
                    trading_symbol,
                    timeframe,
                    semaphore
                )
                for trading_symbol, instrument_key in instruments.items()
            ]
            
            trading_symbols = list(instruments.keys())
            
            logger.info(f"Starting concurrent fetch (max {self.max_concurrent} simultaneous)...")
            
            # Execute all tasks concurrently using gather
            # return_exceptions=True ensures one failure doesn't stop everything
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            progress = ProgressLogger(len(responses), f"Processing {timeframe} results", logger)
            
            success_count = 0
            error_count = 0
            
            for trading_symbol, response in zip(trading_symbols, responses):
                if isinstance(response, Exception):
                    logger.error(f"{trading_symbol}: Failed with error - {response}")
                    error_count += 1
                elif response is not None and not response.empty:
                    results[trading_symbol] = response
                    success_count += 1
                
                progress.update()
            
            progress.complete(f"Success: {success_count}, Failed: {error_count}, Total: {len(instruments)}")
        
        return results
    
    def fetch_instruments_data(self,instruments: Dict[str, str],timeframes: List[str]) -> Dict[str, Dict[str, pd.DataFrame]]:
        logger.info("=" * 20)
        logger.info("FETCHING HISTORICAL DATA")
        logger.info("=" * 20)
        
        all_data = {}
        
        for timeframe in timeframes:
            logger.info(f"\nFetching {timeframe} timeframe data...")
            config = TIMEFRAME_CONFIG.get(timeframe, {})
            logger.info(f"  Interval: {config.get('interval')} {config.get('unit')}")
            logger.info(f"  History: {config.get('days_history')} days")
            
            # Run async fetch
            data = asyncio.run(self.fetch_multiple_instruments(instruments, timeframe))
            all_data[timeframe] = data
            
            if data:
                # Display statistics
                total_candles = sum(len(df) for df in data.values())
                avg_candles = total_candles / len(data) if data else 0
                
                logger.info(f"\n[OK] {timeframe} data fetching complete:")
                logger.info(f"  Instruments fetched: {len(data)}/{len(instruments)}")
                logger.info(f"  Total candles: {total_candles:,}")
                logger.info(f"  Average candles per instrument: {avg_candles:.1f}")
                
                # Sample data
                sample_symbol = list(data.keys())[0]
                sample_df = data[sample_symbol]
                logger.info(f"\n  Sample data ({sample_symbol}):")
                logger.info(f"  Date range: {sample_df['timestamp'].min()} to {sample_df['timestamp'].max()}")
                logger.info(f"  Number of candles: {len(sample_df)}")
            else:
                logger.warning(f"[X] No data fetched for {timeframe} timeframe")
        
        logger.info("\n" + "=" * 20)
        logger.info("DATA FETCHING COMPLETE")
        logger.info("=" * 20)
        
        return all_data
    
    def combine_instrument_data(self,data_by_timeframe: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, pd.DataFrame]:
        
        combined = {}
        
        for timeframe, instruments_data in data_by_timeframe.items():
            if instruments_data:
                # Concatenate all instrument dataframes
                dfs = list(instruments_data.values())
                combined_df = pd.concat(dfs, ignore_index=True)
                
                # Sort by symbol and timestamp
                combined_df = combined_df.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
                
                combined[timeframe] = combined_df
                logger.info(f"Combined {timeframe} data: {len(combined_df)} total rows")
        
        return combined