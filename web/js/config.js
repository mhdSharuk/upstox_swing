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
    MIN_125: '125min.parquet'
  },
  
  // ═══════════════════════════════════════════════════════════
  
  // Apps Script URL for watchlist (keeping existing functionality)
  APPS_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbwwS6lD60PMl1luus7ljYxL590Bd6NeWa69X97Pw2mi17cIOJfVpvTOkc358XwVksP6/exec',
  
  // Supertrend configurations (MUST match Python backend exactly)
  SUPERTRENDS: {
    DAILY: [
      { id: 'ST_daily_sma5', label: 'SMA 5', description: 'Weekly reference with SMA' },
      { id: 'ST_daily_sma20', label: 'SMA 20', description: 'Monthly reference with SMA' },
    //   { id: 'ST_daily_hl2_20', label: 'HL2 20', description: 'Monthly reference without SMA' },
    //   { id: 'ST_daily_hl2_5', label: 'HL2 5', description: 'Weekly reference without SMA' }
    ],
    MIN_125: [
      { id: 'ST_125m_sma15', label: 'SMA 15', description: 'Short-term with SMA 15' },
      { id: 'ST_125m_hl2_15', label: 'HL2 15', description: 'Medium-term with HL2 15' },
    //   { id: 'ST_125m_hl2_10', label: 'HL2 10', description: 'Medium-term without SMA' },
    //   { id: 'ST_125m_hl2_3', label: 'HL2 3', description: 'Short-term without SMA' }
    ]
  }
};

// Generate full URLs for parquet files
CONFIG.PARQUET_URLS = {
  DAILY: `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.FILES.DAILY}`,
  MIN_125: `${CONFIG.SUPABASE_URL}/storage/v1/object/public/${CONFIG.BUCKET_NAME}/${CONFIG.FILES.MIN_125}`
};