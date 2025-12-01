/**
 * Configuration File
 * Update the SUPABASE_URL with your actual Supabase project URL
 */

const CONFIG = {
  // ═══════════════════════════════════════════════════════════
  // 🔧 SUPABASE CONFIGURATION - EDIT THIS VALUE
  // ═══════════════════════════════════════════════════════════
  
  // Your Supabase project URL
  SUPABASE_URL: 'https://wbltdkxjeyggxiogcxxp.supabase.co',
  
  // Storage bucket name (must match your Supabase bucket exactly)
  BUCKET_NAME: 'st-swing-bucket',
  
  // Parquet file names (must match your actual files in Supabase)
  FILES: {
    DAILY: 'daily.parquet',
    MIN_125: '125min.parquet',
    MIN_60: '60min.parquet'
  },
  
  // ═══════════════════════════════════════════════════════════
  
  // Apps Script URL for watchlist (keeping existing functionality)
  APPS_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbwwS6lD60PMl1luus7ljYxL590Bd6NeWa69X97Pw2mi17cIOJfVpvTOkc358XwVksP6/exec',
  
  // Supertrend configurations (MUST match Python backend exactly)
  SUPERTRENDS: {
    DAILY: [
      { id: 'ST_daily_sma5', label: 'SMA 5', description: 'Weekly reference with SMA', atr_period: 5 },
      { id: 'ST_daily_sma20', label: 'SMA 20', description: 'Monthly reference with SMA', atr_period: 20 }
    ],
    MIN_125: [
      { id: 'ST_125m_sma3', label: 'SMA 3', description: 'Short-term with SMA', atr_period: 3 },
      { id: 'ST_125m_sma15', label: 'SMA 15', description: 'Medium-term with SMA', atr_period: 15 }
    ],
    MIN_60: [
      { id: 'ST_60m_sma7', label: 'SMA 7', description: 'Medium-term with SMA', atr_period: 7 },
      { id: 'ST_60m_sma35', label: 'SMA 35', description: 'Long-term with SMA', atr_period: 35 }
    ]
  },
  
  // Strategy configurations for each timeframe (bigger ATR first, shorter ATR second)
  STRATEGY_CONFIGS: {
    daily: {
      bigger: 'ST_daily_sma20',
      shorter: 'ST_daily_sma5'
    },
    min125: {
      bigger: 'ST_125m_sma15',
      shorter: 'ST_125m_sma3'
    },
    min60: {
      bigger: 'ST_60m_sma35',
      shorter: 'ST_60m_sma7'
    }
  }
};

// Generate full URLs for parquet files
CONFIG.PARQUET_URLS = {
  DAILY: `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.FILES.DAILY}`,
  MIN_125: `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.FILES.MIN_125}`,
  MIN_60: `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.FILES.MIN_60}`
};