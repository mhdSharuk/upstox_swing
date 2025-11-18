/* ═══════════════════════════════════════════════════════════
   API COMMUNICATION
   
   Handles all communication with Google Apps Script backend
   ═══════════════════════════════════════════════════════════ */

const API = {
  /**
   * Fetch daily signals from backend
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} Signal data
   */
  async getDailySignals(filters) {
    const params = new URLSearchParams({
      action: 'getDailySignals',
      supertrend: filters.supertrend || '',
      sector: filters.sector || 'All',
      industry: filters.industry || 'All',
      mcap: filters.mcap || CONFIG.DEFAULT_FILTERS.mcap,
      pct: filters.pct || CONFIG.DEFAULT_FILTERS.pct,
      flat: filters.flat || CONFIG.DEFAULT_FILTERS.flat
    });

    const url = `${CONFIG.APPS_SCRIPT_URL}?${params}`;
    console.log('📡 Fetching daily signals...');
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch daily signals');
    }
    
    return data;
  },

  /**
   * Fetch 125min signals from backend
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} Signal data
   */
  async get125minSignals(filters) {
    const params = new URLSearchParams({
      action: 'get125minSignals',
      supertrend: filters.supertrend || '',
      sector: filters.sector || 'All',
      industry: filters.industry || 'All',
      mcap: filters.mcap || CONFIG.DEFAULT_FILTERS.mcap,
      pct: filters.pct || CONFIG.DEFAULT_FILTERS.pct,
      flat: filters.flat || CONFIG.DEFAULT_FILTERS.flat
    });

    const url = `${CONFIG.APPS_SCRIPT_URL}?${params}`;
    console.log('📡 Fetching 125min signals...');
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch 125min signals');
    }
    
    return data;
  },

  /**
   * Fetch watchlist from backend
   * @returns {Promise<Object>} Watchlist data
   */
  async getWatchlist() {
    const url = `${CONFIG.APPS_SCRIPT_URL}?action=getWatchlist`;
    console.log('📡 Fetching watchlist...');
    
    const response = await fetch(url);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to fetch watchlist');
    }
    
    return data;
  },

  /**
   * Add item to watchlist
   * @param {Object} item - Item to add
   */
  async addToWatchlist(item) {
    const params = new URLSearchParams({
      action: 'addToWatchlist',
      symbol: item.symbol,
      sheet: item.sheet,
      supertrend: item.supertrend,
      type: item.type,
      pct: item.pct,
      flatbase: item.flatbase
    });

    const url = `${CONFIG.APPS_SCRIPT_URL}?${params}`;
    console.log(`➕ Adding to watchlist: ${item.symbol}`);
    
    await fetch(url);
  },

  /**
   * Remove item from watchlist
   * @param {Object} item - Item to remove
   */
  async removeFromWatchlist(item) {
    const params = new URLSearchParams({
      action: 'removeFromWatchlist',
      symbol: item.symbol,
      sheet: item.sheet,
      supertrend: item.supertrend,
      type: item.type
    });

    const url = `${CONFIG.APPS_SCRIPT_URL}?${params}`;
    console.log(`➖ Removing from watchlist: ${item.symbol}`);
    
    await fetch(url);
  }
};