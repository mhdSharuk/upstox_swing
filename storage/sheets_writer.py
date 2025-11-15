"""
Google Sheets Writer - Write calculated data to Google Sheets
UPDATED: Removed upperBand/lowerBand, reordered columns (calculations first, company info last)
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import json
from typing import Dict, List, Optional
from config.settings import SHEETS_CONFIG, CANDLE_RETENTION
from utils.logger import get_logger, ProgressLogger

logger = get_logger(__name__)


class GoogleSheetsWriter:
    """
    Write data to Google Sheets with batching and error handling
    """
    
    def __init__(
        self,
        sheet_id: str,
        service_account_file: str
    ):
        """
        Initialize Google Sheets Writer
        
        Args:
            sheet_id: Google Sheets ID
            service_account_file: Path to service account JSON file
        """
        self.sheet_id = sheet_id
        self.service_account_file = service_account_file
        self.batch_size = SHEETS_CONFIG['batch_size']
        self.max_retries = SHEETS_CONFIG['max_retries']
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None


    # ✅ ✅ ADDED: Auto-resize helper ------------------------------------------
    def _ensure_capacity(self, worksheet, rows_needed: int, cols_needed: int):
        """
        Ensure worksheet has enough rows/columns before uploading.
        Prevents: APIError 400 - Range exceeds grid limits.
        """
        try:
            # Expand rows if needed
            if worksheet.row_count < rows_needed:
                to_add = rows_needed - worksheet.row_count
                worksheet.add_rows(to_add)
                logger.info(f"Expanded worksheet rows +{to_add} (now {worksheet.row_count})")

            # Expand columns if needed
            if worksheet.col_count < cols_needed:
                to_add = cols_needed - worksheet.col_count
                worksheet.add_cols(to_add)
                logger.info(f"Expanded worksheet cols +{to_add} (now {worksheet.col_count})")

        except Exception as e:
            logger.error(f"Failed to expand worksheet grid: {e}")
            raise


    # -------------------------------------------------------------------------
    def test_authentication(self) -> tuple[bool, str]:
        """
        Test authentication and access to Google Sheets
        This is a comprehensive test before running the pipeline
        
        Returns:
            tuple: (success: bool, message: str)
        """
        logger.info("\n" + "=" * 20)
        logger.info("TESTING GOOGLE SHEETS AUTHENTICATION")
        logger.info("=" * 20)
        
        # Step 1: Check if service account file exists
        import os
        if not os.path.exists(self.service_account_file):
            error_msg = f"❌ Service account file not found: {self.service_account_file}"
            logger.error(error_msg)
            return False, error_msg
        
        logger.info(f"✓ Service account file found: {self.service_account_file}")
        
        # Step 2: Validate JSON file
        try:
            with open(self.service_account_file, 'r') as f:
                sa_data = json.load(f)
                client_email = sa_data.get('client_email', 'NOT FOUND')
                project_id = sa_data.get('project_id', 'NOT FOUND')
                
            logger.info(f"✓ Service account JSON is valid")
            logger.info(f"  Client Email: {client_email}")
            logger.info(f"  Project ID: {project_id}")
            
            if client_email == 'NOT FOUND':
                error_msg = "❌ 'client_email' not found in service account JSON"
                logger.error(error_msg)
                return False, error_msg
                
        except json.JSONDecodeError as e:
            error_msg = f"❌ Invalid JSON in service account file: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ Error reading service account file: {e}"
            logger.error(error_msg)
            return False, error_msg
        
        # Step 3: Try to authenticate
        try:
            logger.info("\n🔐 Attempting to authenticate with Google Sheets API...")
            
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            credentials = Credentials.from_service_account_file(
                self.service_account_file,
                scopes=scope
            )
            
            self.client = gspread.authorize(credentials)
            logger.info("✓ Successfully created Google Sheets client")
            
        except Exception as e:
            error_msg = f"❌ Failed to create Google Sheets client: {e}"
            logger.error(error_msg)
            logger.error("\nPossible solutions:")
            logger.error("1. Check if the service account JSON file is valid")
            logger.error("2. Ensure Google Sheets API is enabled in your Google Cloud project")
            logger.error("3. Ensure Google Drive API is enabled in your Google Cloud project")
            return False, error_msg
        
        # Step 4: Try to access the specific spreadsheet
        try:
            logger.info(f"\n📊 Attempting to access spreadsheet: {self.sheet_id}")
            
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            
            logger.info(f"✓ Successfully accessed spreadsheet")
            logger.info(f"  Title: {self.spreadsheet.title}")
            logger.info(f"  URL: https://docs.google.com/spreadsheets/d/{self.sheet_id}")
            
        except gspread.exceptions.SpreadsheetNotFound:
            error_msg = f"❌ Spreadsheet not found or no access: {self.sheet_id}"
            logger.error(error_msg)
            logger.error("\n❗ COMMON ISSUE - Sheet not shared with service account")
            logger.error("\nTo fix this:")
            logger.error(f"1. Open sheet: https://docs.google.com/spreadsheets/d/{self.sheet_id}")
            logger.error(f"2. Click 'Share'")
            logger.error(f"3. Add: {client_email}")
            logger.error("4. Give 'Editor' access")
            return False, error_msg
            
        except gspread.exceptions.APIError as e:
            error_msg = f"❌ Google Sheets API error: {e}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"❌ Unexpected error accessing spreadsheet: {e}"
            logger.error(error_msg)
            return False, error_msg
        
        # Step 5: Try to read worksheet list
        try:
            logger.info("\n📋 Testing worksheet access...")
            worksheets = self.spreadsheet.worksheets()
            
            logger.info(f"✓ Retrieved {len(worksheets)} worksheet(s)")
            for ws in worksheets:
                logger.info(f"  - {ws.title}")
                
        except Exception as e:
            error_msg = f"❌ Failed to retrieve worksheets: {e}"
            logger.error(error_msg)
            return False, error_msg
        
        # Step 6: Try to perform a test write
        try:
            logger.info("\n✍️  Testing write permissions...")
            
            test_sheet_name = "_test_access"
            try:
                test_ws = self.spreadsheet.worksheet(test_sheet_name)
            except gspread.WorksheetNotFound:
                test_ws = self.spreadsheet.add_worksheet(title=test_sheet_name, rows=10, cols=5)
            
            test_ws.update('A1', [['Test', 'Access', 'Check']])
            logger.info(f"✓ Test write succeeded")
            
            self.spreadsheet.del_worksheet(test_ws)
            logger.info(f"✓ Test worksheet deleted")
            
        except Exception as e:
            error_msg = f"❌ Write test failed: {e}"
            logger.error(error_msg)
            return False, error_msg
        
        logger.info("\n✅ ALL AUTHENTICATION TESTS PASSED!\n")
        return True, "Authentication successful"
    

    # -------------------------------------------------------------------------
    def authenticate(self) -> bool:
        try:
            logger.info("Authenticating with Google Sheets...")
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(
                self.service_account_file,
                scopes=scope
            )
            
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            
            logger.info(f"✓ Successfully authenticated")
            return True
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    

    # -------------------------------------------------------------------------
    def get_or_create_worksheet(
        self,
        sheet_name: str,
        rows: int = 1000,
        cols: int = 50
    ) -> Optional[gspread.Worksheet]:

        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.clear()
            logger.info(f"Found existing worksheet: {sheet_name}")
            return worksheet
            
        except gspread.WorksheetNotFound:
            logger.info(f"Creating new worksheet: {sheet_name}")
            worksheet = self.spreadsheet.add_worksheet(
                title=sheet_name,
                rows=rows,
                cols=cols
            )
            return worksheet
            
        except Exception as e:
            logger.error(f"Error getting/creating worksheet '{sheet_name}': {e}")
            return None
    

    # -------------------------------------------------------------------------
    def prepare_dataframe_for_upload(
        self,
        df: pd.DataFrame,
        timeframe: str,
        configs: List[dict]
    ) -> pd.DataFrame:
        """
        Prepare DataFrame for upload to Google Sheets
        UPDATED: 
        - Keep latest 3 candles per symbol (retention = 3)
        - Remove upperBand and lowerBand columns
        - Reorder columns: calculations first, company info (sector/industry/market_cap) last
        - Clean NaN, Infinity values for JSON compliance
        """
        retention = CANDLE_RETENTION.get(timeframe, 3)
        
        logger.info(f"Preparing {timeframe} data for upload...")
        logger.info(f"  Retention: Latest {retention} candles per symbol")
        
        # Keep latest 3 candles per symbol
        df_prepared = df.groupby('trading_symbol').apply(
            lambda x: x.nlargest(retention, 'timestamp')
        ).reset_index(drop=True)
        
        df_prepared = df_prepared.sort_values(['trading_symbol', 'timestamp']).reset_index(drop=True)
        
        # Define column order: calculations first, company info last
        # Base columns (OHLC data)
        base_columns = ['trading_symbol', 'timestamp', 'open', 'high', 'low', 'close', 'hl2']
        
        # Supertrend and calculation columns for each config
        calculation_columns = []
        for config in configs:
            name = config['name']
            calculation_columns.extend([
                f'supertrend_{name}',
                f'pct_diff_avg3_{name}',
                f'pct_diff_latest_{name}',
                f'direction_{name}',
                f'flatbase_count_{name}'
            ])
        
        # Company info columns (at the end)
        company_info_columns = ['sector', 'industry', 'market_cap']
        
        # Combine all columns in the desired order
        all_columns = base_columns + calculation_columns + company_info_columns
        
        # Filter to only include columns that exist in the dataframe
        available_columns = [col for col in all_columns if col in df_prepared.columns]
        
        # Note: upperBand and lowerBand are automatically excluded since they're not in all_columns
        
        df_prepared = df_prepared[available_columns]
        
        # CRITICAL: Clean data for JSON compliance
        # Replace NaN, Infinity, -Infinity with None (which becomes null in JSON)
        df_prepared = self._clean_data_for_json(df_prepared)
        
        df_prepared['timestamp'] = df_prepared['timestamp'].astype(str)
        
        logger.info(f"✓ Prepared {len(df_prepared)} rows with {len(available_columns)} columns")
        logger.info(f"  Columns: {', '.join(available_columns[:10])}{'...' if len(available_columns) > 10 else ''}")
        
        return df_prepared
    
    def _clean_data_for_json(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame to ensure JSON compliance for Google Sheets
        Replaces NaN, Infinity, -Infinity with None
        
        Args:
            df: DataFrame to clean
        
        Returns:
            pd.DataFrame: Cleaned DataFrame
        """
        import numpy as np
        
        # Make a copy to avoid modifying original
        df_clean = df.copy()
        
        # Count issues before cleaning
        nan_count = df_clean.isna().sum().sum()
        inf_count = np.isinf(df_clean.select_dtypes(include=[np.number])).sum().sum()
        
        if nan_count > 0 or inf_count > 0:
            logger.info(f"  Cleaning data: {nan_count} NaN values, {inf_count} Infinity values")
        
        # Replace NaN with None (becomes null in JSON)
        df_clean = df_clean.where(pd.notna(df_clean), None)
        
        # Replace Infinity and -Infinity with None for numeric columns
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # Replace inf and -inf with None
            df_clean[col] = df_clean[col].replace([np.inf, -np.inf], None)
        
        logger.info(f"  ✓ Data cleaned for JSON compliance")
        
        return df_clean
    

    # -------------------------------------------------------------------------
    def write_dataframe_to_sheet(
        self,
        worksheet: gspread.Worksheet,
        df: pd.DataFrame
    ) -> bool:

        try:
            logger.info(f"Writing {len(df)} rows to {worksheet.title}...")
            
            df.fillna('None', inplace=True)
            # df.to_csv('write_worksheet_title.csv', index=False)

            # HEADER + ROWS
            data = [df.columns.tolist()] + df.values.tolist()

            # ✅ ✅ NEW: Ensure row/col capacity BEFORE writing
            self._ensure_capacity(
                worksheet,
                rows_needed=len(data) + 5,
                cols_needed=len(df.columns) + 5
            )

            num_batches = (len(data) + self.batch_size - 1) // self.batch_size
            logger.info(f"  Uploading in {num_batches} batches of {self.batch_size}")

            progress = ProgressLogger(len(data), f"Uploading to {worksheet.title}", logger)

            for i in range(0, len(data), self.batch_size):
                batch = data[i:i + self.batch_size]
                start_row = i + 1
                
                for attempt in range(self.max_retries):
                    try:
                        worksheet.update(
                            f'A{start_row}',
                            batch,
                            value_input_option='RAW'
                        )
                        
                        progress.update(len(batch))
                        time.sleep(0.5)
                        break
                        
                    except gspread.exceptions.APIError as e:
                        if 'RATE_LIMIT_EXCEEDED' in str(e) or 'Quota exceeded' in str(e):
                            wait_time = (attempt + 1) * 5
                            logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                            time.sleep(wait_time)
                            if attempt == self.max_retries - 1:
                                raise
                        else:
                            raise
            
            progress.complete(f"{len(data)} rows uploaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error writing to sheet: {e}")
            return False
    

    # -------------------------------------------------------------------------
    def write_timeframe_data(
        self,
        df: pd.DataFrame,
        timeframe: str,
        configs: List[dict]
    ) -> bool:

        logger.info("=" * 20)
        logger.info(f"WRITING {timeframe.upper()} DATA TO GOOGLE SHEETS")
        logger.info("=" * 20)
        
        sheet_name = SHEETS_CONFIG['sheet_names'].get(timeframe)
        if not sheet_name:
            logger.error(f"No sheet name configured for timeframe: {timeframe}")
            return False
        
        df_prepared = self.prepare_dataframe_for_upload(df, timeframe, configs)
        
        if df_prepared.empty:
            logger.warning(f"No data to write for {timeframe}")
            return False
        
        worksheet = self.get_or_create_worksheet(sheet_name)
        if not worksheet:
            return False
        
        success = self.write_dataframe_to_sheet(worksheet, df_prepared)
        
        if success:
            logger.info(f"✓ Successfully wrote {timeframe} data to Google Sheets")
        else:
            logger.error(f"✗ Failed to write {timeframe} data")
        
        logger.info("=" * 20)
        return success


    # -------------------------------------------------------------------------
    def write_all_data(
        self,
        data_dict: Dict[str, pd.DataFrame],
        configs_dict: Dict[str, List[dict]]
    ) -> bool:
        """
        Write all timeframe data to Google Sheets
        
        Args:
            data_dict: Dictionary mapping timeframe to combined DataFrame
            configs_dict: Dictionary mapping timeframe to configs
        
        Returns:
            bool: True if all writes successful
        """
        if not self.client or not self.spreadsheet:
            logger.error("Not authenticated. Call authenticate() first.")
            return False
        
        logger.info("\n" + "=" * 20)
        logger.info("WRITING DATA TO GOOGLE SHEETS")
        logger.info("=" * 20)
        logger.info(f"Spreadsheet: {self.spreadsheet.title}")
        logger.info(f"Timeframes to write: {list(data_dict.keys())}")
        logger.info("=" * 20 + "\n")
        
        all_success = True
        
        for timeframe, df in data_dict.items():
            configs = configs_dict.get(timeframe, [])
            success = self.write_timeframe_data(df, timeframe, configs)
            
            if not success:
                all_success = False
                logger.error(f"Failed to write {timeframe} data")
            
            time.sleep(2)
        
        if all_success:
            logger.info("\n✓ All data written successfully!")
            logger.info(f"https://docs.google.com/spreadsheets/d/{self.sheet_id}")
        else:
            logger.warning("\n⚠ Some writes failed")
        
        return all_success