/* ═══════════════════════════════════════════════════════════
   WATCHLIST OPERATIONS
   
   Manages watchlist data and operations (add, remove, check)
   ═══════════════════════════════════════════════════════════ */

const WatchlistManager = {
  data: [],

  /**
   * Load watchlist silently (no UI updates)
   * Used for parallel loading to check item status
   */
  async loadSilent() {
    try {
      const result = await API.getWatchlist();
      this.data = result.watchlist || [];
      console.log(`📋 Watchlist loaded silently: ${this.data.length} items`);
    } catch (error) {
      console.error('❌ Error loading watchlist silently:', error);
    }
  },

  /**
   * Load watchlist with UI updates
   * @returns {Promise<void>}
   */
  async load() {
    console.log('📡 Loading watchlist...');
    const startTime = performance.now();

    try {
      UI.setLoading('watchlist', true);

      const result = await API.getWatchlist();
      this.data = result.watchlist || [];

      UI.renderWatchlist(this.data);

      const loadTime = Math.round(performance.now() - startTime);
      UI.updateTimestamp('watchlist', loadTime);

      console.log(`✅ Watchlist loaded in ${loadTime}ms`);
    } catch (error) {
      console.error('❌ Error loading watchlist:', error);
      alert('Error loading watchlist: ' + error.message);
    } finally {
      UI.setLoading('watchlist', false);
    }
  },

  /**
   * Check if an item exists in watchlist
   * @param {string} symbol - Stock symbol
   * @param {string} sheet - Sheet name
   * @param {string} supertrend - Supertrend value
   * @param {string} type - Signal type (Long/Short)
   * @returns {boolean}
   */
  checkExists(symbol, sheet, supertrend, type) {
    return this.data.some(item =>
      item.symbol === symbol &&
      item.sheet === sheet &&
      item.supertrend === supertrend &&
      item.type === type
    );
  },

  /**
   * Add item to watchlist
   * @param {Object} item - Item to add
   */
  async add(item) {
    try {
      await API.addToWatchlist(item);
      console.log(`✅ Added to watchlist: ${item.symbol}`);

      // Reload silently after delay
      setTimeout(() => this.loadSilent(), CONFIG.UI.loadingDelay);
    } catch (error) {
      console.error('❌ Error adding to watchlist:', error);
    }
  },

  /**
   * Remove item from watchlist
   * @param {Object} item - Item to remove
   */
  async remove(item) {
    try {
      await API.removeFromWatchlist(item);
      console.log(`✅ Removed from watchlist: ${item.symbol}`);

      // Reload silently after delay
      setTimeout(() => this.loadSilent(), CONFIG.UI.loadingDelay);
    } catch (error) {
      console.error('❌ Error removing from watchlist:', error);
    }
  }
};

/**
 * Global function: Toggle watchlist item from signals table
 */
async function toggleWatchlist(checkbox, symbol, sheet, supertrend, type, pct, flatbase) {
  const item = { symbol, sheet, supertrend, type, pct, flatbase };

  if (checkbox.checked) {
    await WatchlistManager.add(item);
  } else {
    await WatchlistManager.remove(item);
  }
}

/**
 * Global function: Remove item from watchlist UI
 */
async function removeFromWatchlistUI(checkbox, symbol, sheet, supertrend, type) {
  if (!checkbox.checked) {
    const item = { symbol, sheet, supertrend, type };
    await WatchlistManager.remove(item);

    // Reload watchlist and current tab after delay
    setTimeout(() => {
      WatchlistManager.load();
      if (AppState.currentTab === 'daily') loadDailySignals();
      if (AppState.currentTab === '125min') load125minSignals();
    }, CONFIG.UI.loadingDelay);
  }
}

/**
 * Global function: Load watchlist
 */
function loadWatchlist() {
  WatchlistManager.load();
}