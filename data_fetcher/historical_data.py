"""
Historical Data Fetcher - Async data fetching from Upstox
UPDATED: Added SSL context for PythonAnywhere compatibility
"""

import asyncio
import aiohttp
import ssl
import certifi
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz
from config.settings import API_CONFIG, TIMEFRAME_CONFIG, ASYNC_CONFIG
from utils.logger import get_logger, ProgressLogger
from utils.validators import DataValidator

logger = get_logger(__name__)


class HistoricalDataFetcher:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = API_CONFIG['base_url']
        self.historical_endpoint = API_CONFIG['historical_endpoint']
        self.intraday_endpoint = API_CONFIG['intraday_endpoint']
        self.market_status_endpoint = API_CONFIG['market_status_endpoint']
        self.rate_limit_delay = API_CONFIG['rate_limit_delay']
        self.max_retries = API_CONFIG['max_retries']
        self.retry_delay = API_CONFIG['retry_delay']
        self.max_concurrent = ASYNC_CONFIG['max_concurrent_requests']
        self.ist_tz = pytz.timezone('Asia/Kolkata')
    
    async def check_market_status(self, session: aiohttp.ClientSession) -> bool:
        """Check if NSE market is currently open"""
        url = f"{self.base_url}{self.market_status_endpoint}/NSE"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get("status") != "success":
                        return False
                    
                    market_data = data.get("data", {})
                    if not market_data:
                        return False
                    
                    market_status = market_data.get("status", "").upper()
                    is_open = "OPEN" in market_status
                    
                    logger.info(f"NSE Market Status: {market_status}")
                    return is_open
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def _get_date_range(self, timeframe: str) -> Tuple[str, str]:
        """Calculate date range for historical data fetch"""
        to_date = datetime.now()
        to_date_str = to_date.strftime('%Y-%m-%d')
        
        config = TIMEFRAME_CONFIG.get(timeframe, {})
        days_history = config.get('days_history', 90)
        
        from_date = to_date - timedelta(days=days_history)
        from_date_str = from_date.strftime('%Y-%m-%d')
        
        return from_date_str, to_date_str
    
    async def fetch_candle_data(
        self,
        session: aiohttp.ClientSession,
        instrument_key: str,
        trading_symbol: str,
        timeframe: str,
        semaphore: asyncio.Semaphore,
        is_intraday: bool = False
    ) -> Optional[pd.DataFrame]:
        """Fetch candle data for a single instrument"""
        async with semaphore:
            config = TIMEFRAME_CONFIG.get(timeframe, {})
            unit = config['unit']
            interval = config['interval']
            
            if is_intraday:
                url = f"{self.base_url}{self.intraday_endpoint}/{instrument_key}/{unit}/{interval}"
                data_source = "intraday"
            else:
                from_date, to_date = self._get_date_range(timeframe)
                url = f"{self.base_url}{self.historical_endpoint}/{instrument_key}/{unit}/{interval}/{to_date}/{from_date}"
                data_source = "historical"
            
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            for attempt in range(self.max_retries):
                try:
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            if data.get("status") != "success":
                                return None
                            
                            candles = data.get("data", {}).get("candles", [])
                            if not candles:
                                return None
                            
                            df = pd.DataFrame(candles, columns=[
                                "timestamp", "open", "high", "low", "close", "volume", "open_interest"
                            ])

                            # SAFETY CHECK: Validate DataFrame immediately after creation
                            if df.empty:
                                logger.warning(f"{trading_symbol} ({data_source}): No candles returned from API")
                                return None

                            if len(df.columns) == 0:
                                logger.warning(f"{trading_symbol} ({data_source}): DataFrame has no columns")
                                return None

                            # Verify all expected columns are present
                            expected_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                            missing_cols = [col for col in expected_cols if col not in df.columns]
                            if missing_cols:
                                logger.warning(f"{trading_symbol} ({data_source}): Missing columns {missing_cols}")
                                return None

                            # Now safe to process - columns definitely exist
                            df['timestamp'] = pd.to_datetime(df['timestamp'])
                            df['trading_symbol'] = trading_symbol
                            df['hl2'] = (df['high'] + df['low']) / 2
                            df = df.sort_values('timestamp').reset_index(drop=True)

                            is_valid, message = DataValidator.validate_candle_data(df)
                            if not is_valid:
                                logger.warning(f"{trading_symbol} ({data_source}): Validation failed - {message}")
                                return None

                            return df
                        
                        elif response.status == 429:
                            wait_time = self.retry_delay * (attempt + 1)
                            logger.warning(f"{trading_symbol} ({data_source}): Rate limit, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        elif response.status == 401:
                            logger.error(f"{trading_symbol} ({data_source}): Authentication error")
                            return None
                        
                        else:
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay)
                                continue
                            return None
                
                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return None
                
                except Exception as e:
                    logger.error(f"{trading_symbol} ({data_source}): Error - {e}")
                    return None
            
            return None
    
    def _combine_historical_and_intraday(
        self,
        historical_df: Optional[pd.DataFrame],
        intraday_df: Optional[pd.DataFrame],
        trading_symbol: str
    ) -> Optional[pd.DataFrame]:
        """Combine historical and intraday data, removing duplicates"""
        if historical_df is not None and intraday_df is None:
            return historical_df
        
        if intraday_df is not None and historical_df is None:
            return intraday_df
        
        if historical_df is None and intraday_df is None:
            return None
        
        try:
            combined = pd.concat([historical_df, intraday_df], ignore_index=True)
            combined = combined.sort_values('timestamp').reset_index(drop=True)
            
            initial_count = len(combined)
            combined = combined.drop_duplicates(subset=['timestamp'], keep='last')
            duplicates_removed = initial_count - len(combined)
            
            if duplicates_removed > 0:
                logger.info(f"{trading_symbol}: Removed {duplicates_removed} duplicate timestamps")
            
            return combined
            
        except Exception as e:
            logger.error(f"{trading_symbol}: Error combining data - {e}")
            return historical_df
    
    async def fetch_instrument_with_intraday(
        self,
        session: aiohttp.ClientSession,
        instrument_key: str,
        trading_symbol: str,
        timeframe: str,
        semaphore: asyncio.Semaphore,
        market_is_open: bool
    ) -> Optional[pd.DataFrame]:
        """Fetch both historical and intraday data for an instrument"""
        # Fetch historical data
        historical_df = await self.fetch_candle_data(
            session,
            instrument_key,
            trading_symbol,
            timeframe,
            semaphore,
            is_intraday=False
        )
        
        # MODIFIED: Always fetch intraday data regardless of market hours
        intraday_df = await self.fetch_candle_data(
            session,
            instrument_key,
            trading_symbol,
            timeframe,
            semaphore,
            is_intraday=True
        )
        
        # Combine both datasets
        combined_df = self._combine_historical_and_intraday(
            historical_df,
            intraday_df,
            trading_symbol
        )
        
        return combined_df
    
    async def fetch_multiple_instruments(
        self,
        instruments: Dict[str, str],
        timeframe: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple instruments concurrently
        UPDATED: Added SSL context for PythonAnywhere compatibility
        """
        logger.info(f"Fetching {timeframe} data for {len(instruments)} instruments...")
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = {}
        
        # Create SSL context with certifi for PythonAnywhere compatibility
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        # Create connector with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        # Create session with the connector
        async with aiohttp.ClientSession(connector=connector) as session:
            logger.info("Checking NSE market status...")
            market_is_open = await self.check_market_status(session)
            
            # MODIFIED: Always fetch both historical and intraday data
            if market_is_open:
                logger.info("Market is OPEN - fetching historical + intraday data")
            else:
                logger.info("Market is CLOSED - still fetching historical + intraday data")
            
            tasks = []
            symbols = []
            for trading_symbol, instrument_key in instruments.items():
                task = asyncio.create_task(
                    self.fetch_instrument_with_intraday(
                        session,
                        instrument_key,
                        trading_symbol,
                        timeframe,
                        semaphore,
                        market_is_open
                    )
                )
                tasks.append(task)
                symbols.append(trading_symbol)
            
            total = len(tasks)
            completed = 0
            success_count = 0
            error_count = 0
            last_percentage = -1
            
            logger.info(f"Starting concurrent fetch (max {self.max_concurrent} simultaneous)...")
            
            pending = set(tasks)
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                
                for task in done:
                    idx = tasks.index(task)
                    trading_symbol = symbols[idx]
                    
                    try:
                        response = task.result()
                        
                        if response is not None and not response.empty:
                            results[trading_symbol] = response
                            success_count += 1
                        else:
                            error_count += 1
                        
                    except Exception as e:
                        error_count += 1
                    
                    completed += 1
                    percentage = int((completed / total) * 100)
                    
                    if percentage >= last_percentage + 10 or completed == total:
                        logger.info(f"Progress: {completed}/{total} ({percentage}%)")
                        last_percentage = percentage
            
            logger.info(f"✓ Fetch complete: Success: {success_count}, Failed: {error_count}, Total: {total}")
        
        return results
    
    def fetch_instruments_data(
        self,
        instruments: Dict[str, str],
        timeframes: List[str]
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Fetch data for all instruments across multiple timeframes"""
        logger.info("=" * 60)
        logger.info("FETCHING HISTORICAL & INTRADAY DATA")
        logger.info("=" * 60)
        
        all_data = {}
        
        for timeframe in timeframes:
            logger.info(f"\nFetching {timeframe} timeframe data...")
            config = TIMEFRAME_CONFIG.get(timeframe, {})
            logger.info(f"  Interval: {config.get('interval')} {config.get('unit')}")
            logger.info(f"  History: {config.get('days_history')} days")
            
            data = asyncio.run(self.fetch_multiple_instruments(instruments, timeframe))
            all_data[timeframe] = data
            
            if data:
                total_candles = sum(len(df) for df in data.values())
                avg_candles = total_candles / len(data) if data else 0
                
                logger.info(f"\n✓ {timeframe} data fetching complete:")
                logger.info(f"  Instruments fetched: {len(data)}/{len(instruments)}")
                logger.info(f"  Total candles: {total_candles:,}")
                logger.info(f"  Average candles per instrument: {avg_candles:.1f}")
                
                sample_symbol = list(data.keys())[0]
                sample_df = data[sample_symbol]
                logger.info(f"\n  Sample data ({sample_symbol}):")
                logger.info(f"  Date range: {sample_df['timestamp'].min()} to {sample_df['timestamp'].max()}")
                logger.info(f"  Number of candles: {len(sample_df)}")
            else:
                logger.warning(f"✗ No data fetched for {timeframe} timeframe")
        
        logger.info("\n" + "=" * 60)
        logger.info("DATA FETCHING COMPLETE")
        logger.info("=" * 60)
        
        return all_data
    
    def combine_instrument_data(
        self,
        data_by_timeframe: Dict[str, Dict[str, pd.DataFrame]]
    ) -> Dict[str, pd.DataFrame]:
        """Combine all instruments data for each timeframe"""
        combined = {}
        
        for timeframe, instruments_data in data_by_timeframe.items():
            if instruments_data:
                dfs = list(instruments_data.values())
                combined_df = pd.concat(dfs, ignore_index=True)
                combined_df = combined_df.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
                combined[timeframe] = combined_df
                logger.info(f"Combined {timeframe} data: {len(combined_df)} total rows")
        
        return combined