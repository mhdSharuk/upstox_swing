/**
 * Configuration File - Simplified for 125min Data Only
 */

const CONFIG = {
  // Supabase Configuration
  SUPABASE_URL: 'https://wbltdkxjeyggxiogcxxp.supabase.co',
  BUCKET_NAME: 'st-swing-bucket',
  
  // Parquet file (125min only)
  PARQUET_FILE: '125min.parquet',
  
  // Supertrend configurations (from config/settings.py)
  SUPERTRENDS: {
    LARGER: 'ST_125m_sma15',  // Larger ATR period (15)
    SHORTER: 'ST_125m_sma3'   // Shorter ATR period (3)
  },
  
  // Column names in parquet file
  COLUMNS: {
    TIMESTAMP: 'timestamp',
    OPEN: 'open',
    HIGH: 'high',
    LOW: 'low',
    CLOSE: 'close',
    VOLUME: 'volume',
    SYMBOL: 'trading_symbol',
    
    // Larger ATR (sma15)
    SUPERTREND_LARGER: 'supertrend_ST_125m_sma15',
    DIRECTION_LARGER: 'direction_ST_125m_sma15',
    UPPERBAND_LARGER: 'upperBand_ST_125m_sma15',
    LOWERBAND_LARGER: 'lowerBand_ST_125m_sma15',
    
    // Shorter ATR (sma3)
    SUPERTREND_SHORTER: 'supertrend_ST_125m_sma3',
    DIRECTION_SHORTER: 'direction_ST_125m_sma3',
    UPPERBAND_SHORTER: 'upperBand_ST_125m_sma3',
    LOWERBAND_SHORTER: 'lowerBand_ST_125m_sma3',
    
    // Percentage diff
    PCT_DIFF: 'pct_diff_close_lowerband_ST_125m_sma3'
  }
};

// Generate parquet URL
CONFIG.PARQUET_URL = `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.PARQUET_FILE}`;

console.log('✅ CONFIG loaded:', {
  url: CONFIG.PARQUET_URL,
  supertrends: CONFIG.SUPERTRENDS
});