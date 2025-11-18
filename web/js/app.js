/* ═══════════════════════════════════════════════════════════
   MAIN APPLICATION
   
   Application initialization and tab management
   ═══════════════════════════════════════════════════════════ */

const AppState = {
  currentTab: 'daily',
  isLoading: false
};

/**
 * Switch between tabs
 * @param {string} tab - Tab name (daily, 125min, watchlist)
 */
function switchTab(tab) {
  AppState.currentTab = tab;

  // Update tab buttons
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');

  // Update tab content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(tab + '-tab').classList.add('active');

  // Load data for tab if needed
  if (tab === '125min') {
    load125minSignals();
  } else if (tab === 'watchlist') {
    loadWatchlist();
  }
}

/**
 * Load daily signals
 */
async function loadDailySignals() {
  if (AppState.isLoading) return;
  AppState.isLoading = true;

  console.log('📡 Loading daily signals...');
  const startTime = performance.now();

  try {
    UI.setLoading('daily', true);

    const filters = UI.getFilters('daily');

    // Parallel loading: Fetch data and watchlist simultaneously
    const [data] = await Promise.all([
      API.getDailySignals(filters),
      WatchlistManager.loadSilent()
    ]);

    // Initialize filters if first load
    if (!UI.areFiltersInitialized('daily')) {
      UI.initializeFilters('daily', data);
    }

    // Render signals
    UI.renderSignals('daily', data.longSignals, data.shortSignals, 'daily_signals');

    // Update timestamp
    const loadTime = Math.round(performance.now() - startTime);
    UI.updateTimestamp('daily', loadTime);

    console.log(`✅ Daily signals loaded in ${loadTime}ms`);
  } catch (error) {
    console.error('❌ Error loading daily signals:', error);
    alert('Error loading daily signals: ' + error.message);
  } finally {
    AppState.isLoading = false;
    UI.setLoading('daily', false);
  }
}

/**
 * Load 125min signals
 */
async function load125minSignals() {
  if (AppState.isLoading) return;
  AppState.isLoading = true;

  console.log('📡 Loading 125min signals...');
  const startTime = performance.now();

  try {
    UI.setLoading('min125', true);

    const filters = UI.getFilters('min125');

    // Parallel loading: Fetch data and watchlist simultaneously
    const [data] = await Promise.all([
      API.get125minSignals(filters),
      WatchlistManager.loadSilent()
    ]);

    // Initialize filters if first load
    if (!UI.areFiltersInitialized('min125')) {
      UI.initializeFilters('min125', data);
    }

    // Render signals
    UI.renderSignals('min125', data.longSignals, data.shortSignals, '125min_signals');

    // Update timestamp
    const loadTime = Math.round(performance.now() - startTime);
    UI.updateTimestamp('min125', loadTime);

    console.log(`✅ 125min signals loaded in ${loadTime}ms`);
  } catch (error) {
    console.error('❌ Error loading 125min signals:', error);
    alert('Error loading 125min signals: ' + error.message);
  } finally {
    AppState.isLoading = false;
    UI.setLoading('min125', false);
  }
}

/**
 * Initialize application
 */
function initApp() {
  console.log('🚀 Signal Tracker initializing...');

  // Initialize theme
  ThemeManager.init();

  // Validate configuration
  if (!CONFIG.APPS_SCRIPT_URL || CONFIG.APPS_SCRIPT_URL === 'YOUR_APPS_SCRIPT_URL_HERE') {
    alert('⚠️ Configuration Error: Please set APPS_SCRIPT_URL in js/config.js');
    return;
  }

  // Load initial data
  loadDailySignals();

  console.log('✅ Signal Tracker initialized');
}

/**
 * Window load event
 */
window.onload = function () {
  initApp();
};