/* ═══════════════════════════════════════════════════════════
   CONFIGURATION
   ═══════════════════════════════════════════════════════════
   
   ⚠️  IMPORTANT: Edit the APPS_SCRIPT_URL below
   
   This is the URL from your Google Apps Script deployment.
   Replace with your actual Apps Script Web App URL.
   
   ═══════════════════════════════════════════════════════════ */

const CONFIG = {
  // 🔧 EDIT THIS URL
  APPS_SCRIPT_URL: 'https://script.google.com/macros/s/AKfycbwwS6lD60PMl1luus7ljYxL590Bd6NeWa69X97Pw2mi17cIOJfVpvTOkc358XwVksP6/exec',
  
  // Default filter values
  DEFAULT_FILTERS: {
    mcap: 10000,
    pct: 2.5,
    flat: 3
  },
  
  // UI settings
  UI: {
    maxTableHeight: 600,
    loadingDelay: 500
  }
};

// Validate configuration on load
if (!CONFIG.APPS_SCRIPT_URL || CONFIG.APPS_SCRIPT_URL === 'YOUR_APPS_SCRIPT_URL_HERE') {
  console.error('⚠️ APPS_SCRIPT_URL not configured!');
}