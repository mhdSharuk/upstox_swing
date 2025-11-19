/**
 * Main Application Module
 * Orchestrates all functionality - tabs, data loading, filtering, rendering
 * UPDATED: Hardcoded supertrend values for instant switching
 */

// Global state
let watchlistData = [];
let currentTab = 'daily';
let isLoading = false;
let symbolsTabInitialized = false;

// ═══════════════════════════════════════════════════════════
// THEME MANAGEMENT
// ═══════════════════════════════════════════════════════════

function toggleTheme() {
  const html = document.documentElement;
  const currentTheme = html.getAttribute('data-theme');
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  
  html.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  
  updateThemeButton(newTheme);
  chartRenderer.updateChartsTheme();
}

function updateThemeButton(theme) {
  const icon = document.getElementById('theme-icon');
  const text = document.getElementById('theme-text');
  
  if (theme === 'dark') {
    icon.textContent = '☀️';
    text.textContent = 'Light Mode';
  } else {
    icon.textContent = '🌙';
    text.textContent = 'Dark Mode';
  }
}

function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeButton(savedTheme);
}

// ═══════════════════════════════════════════════════════════
// TAB MANAGEMENT
// ═══════════════════════════════════════════════════════════

function switchTab(tab) {
  currentTab = tab;
  
  // Update tab buttons
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  
  // Update tab content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(tab + '-tab').classList.add('active');
  
  // Load data for the tab
  if (tab === 'daily') {
    loadDailySignals();
  } else if (tab === '125min') {
    load125minSignals();
  } else if (tab === 'watchlist') {
    loadWatchlist();
  } else if (tab === 'charts') {
    loadChartsTab();
  } else if (tab === 'symbols') {
    loadSymbolsTab();
  }
}

// ═══════════════════════════════════════════════════════════
// DAILY SIGNALS TAB
// ═══════════════════════════════════════════════════════════

async function loadDailySignals(forceRefresh = false) {
  if (isLoading) return;
  isLoading = true;
  
  console.log('📡 Loading daily signals...');
  const startTime = performance.now();
  
  try {
    // Disable button and show loading
    const refreshBtn = document.getElementById('daily-refresh-btn');
    refreshBtn.disabled = true;
    refreshBtn.textContent = forceRefresh ? '⏳ Refreshing from server...' : '⏳ Loading...';
    
    document.getElementById('daily-loading').style.display = 'block';
    document.getElementById('daily-content').style.display = 'none';
    
    // Clear cache if force refresh
    if (forceRefresh) {
      await dataLoader.clearCache();
      dataLoader.dailyData = null;
    }
    
    // Load data from parquet
    const data = await dataLoader.getData('daily');
    
    // Populate filter dropdowns on first load
    if (!filtersManager.currentFilters.daily.supertrend) {
      filtersManager.populateFilterDropdowns('daily', data);
    }
    
    // Get current filter values
    const filters = filtersManager.getCurrentFilters('daily');
    const supertrendConfig = filters.supertrend;
    
    // Apply filters and get signals
    const signals = filtersManager.applyFilters(data, filters, supertrendConfig);
    
    // Render tables
    renderSignalsTable('daily-long-tbody', signals.long, 'daily', supertrendConfig);
    renderSignalsTable('daily-short-tbody', signals.short, 'daily', supertrendConfig);
    
    // Update counts
    document.getElementById('daily-long-count').textContent = signals.long.length;
    document.getElementById('daily-short-count').textContent = signals.short.length;
    
    // Show content
    document.getElementById('daily-loading').style.display = 'none';
    document.getElementById('daily-content').style.display = 'block';
    
    // Update last updated
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    document.getElementById('daily-last-updated').textContent = 
      `Updated: ${new Date().toLocaleTimeString()} (${elapsed}s)`;
    
    refreshBtn.disabled = false;
    refreshBtn.textContent = '🔄 Refresh';
    
    console.log(`✓ Daily signals loaded in ${elapsed}s`);
    
  } catch (error) {
    console.error('❌ Error loading daily signals:', error);
    alert('Error loading daily signals: ' + error.message);
    
    document.getElementById('daily-loading').style.display = 'none';
    const refreshBtn = document.getElementById('daily-refresh-btn');
    refreshBtn.disabled = false;
    refreshBtn.textContent = '🔄 Refresh';
  } finally {
    isLoading = false;
  }
}

// ═══════════════════════════════════════════════════════════
// 125MIN SIGNALS TAB
// ═══════════════════════════════════════════════════════════

async function load125minSignals(forceRefresh = false) {
  if (isLoading) return;
  isLoading = true;
  
  console.log('📡 Loading 125min signals...');
  const startTime = performance.now();
  
  try {
    // Disable button and show loading
    const refreshBtn = document.getElementById('min125-refresh-btn');
    refreshBtn.disabled = true;
    refreshBtn.textContent = forceRefresh ? '⏳ Refreshing from server...' : '⏳ Loading...';
    
    document.getElementById('min125-loading').style.display = 'block';
    document.getElementById('min125-content').style.display = 'none';
    
    // Clear cache if force refresh
    if (forceRefresh) {
      await dataLoader.clearCache();
      dataLoader.min125Data = null;
    }
    
    // Load data from parquet
    const data = await dataLoader.getData('min125');
    
    // Populate filter dropdowns on first load
    if (!filtersManager.currentFilters.min125.supertrend) {
      filtersManager.populateFilterDropdowns('min125', data);
    }
    
    // Get current filter values
    const filters = filtersManager.getCurrentFilters('min125');
    const supertrendConfig = filters.supertrend;
    
    // Apply filters and get signals
    const signals = filtersManager.applyFilters(data, filters, supertrendConfig);
    
    // Render tables
    renderSignalsTable('min125-long-tbody', signals.long, 'min125', supertrendConfig);
    renderSignalsTable('min125-short-tbody', signals.short, 'min125', supertrendConfig);
    
    // Update counts
    document.getElementById('min125-long-count').textContent = signals.long.length;
    document.getElementById('min125-short-count').textContent = signals.short.length;
    
    // Show content
    document.getElementById('min125-loading').style.display = 'none';
    document.getElementById('min125-content').style.display = 'block';
    
    // Update last updated
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    document.getElementById('min125-last-updated').textContent = 
      `Updated: ${new Date().toLocaleTimeString()} (${elapsed}s)`;
    
    refreshBtn.disabled = false;
    refreshBtn.textContent = '🔄 Refresh';
    
    console.log(`✓ 125min signals loaded in ${elapsed}s`);
    
  } catch (error) {
    console.error('❌ Error loading 125min signals:', error);
    alert('Error loading 125min signals: ' + error.message);
    
    document.getElementById('min125-loading').style.display = 'none';
    const refreshBtn = document.getElementById('min125-refresh-btn');
    refreshBtn.disabled = false;
    refreshBtn.textContent = '🔄 Refresh';
  } finally {
    isLoading = false;
  }
}

// ═══════════════════════════════════════════════════════════
// CHARTS TAB
// ═══════════════════════════════════════════════════════════

async function loadChartsTab() {
  console.log('📊 Loading charts tab...');
  
  // Get initial data source
  const dataSource = document.getElementById('charts-data').value || 'daily';
  
  // Load data for initial timeframe
  const data = await dataLoader.getData(dataSource);
  
  // Populate all filter dropdowns (including Sector, Industry)
  await filtersManager.populateChartFilters(dataSource, data);
  
  // Load charts with current filters
  await loadCharts();
}

async function loadCharts() {
  console.log('📊 Loading charts...');
  const startTime = performance.now();
  
  try {
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-content').style.display = 'none';
    
    // Get chart filters (now includes Sector, Industry, Market Cap)
    const chartFilters = filtersManager.getCurrentFilters('charts');
    
    // Load data for selected timeframe
    const timeframe = chartFilters.data;
    const data = await dataLoader.getData(timeframe);
    
    console.log('📊 Chart filters:', chartFilters);
    
    // Filter symbols based on chart filters (all filters from Charts tab)
    const filteredSymbols = filtersManager.filterSymbolsForCharts(data, chartFilters);
    
    console.log(`Found ${filteredSymbols.length} symbols matching all filters`);
    
    // Render charts
    await chartRenderer.renderChartsGrid(filteredSymbols, chartFilters.supertrend, timeframe);
    
    // Show content
    document.getElementById('charts-loading').style.display = 'none';
    document.getElementById('charts-content').style.display = 'block';
    
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    console.log(`✓ Charts loaded in ${elapsed}s`);
    
  } catch (error) {
    console.error('❌ Error loading charts:', error);
    alert('Error loading charts: ' + error.message);
    document.getElementById('charts-loading').style.display = 'none';
  }
}

// Handle chart data source change - immediately update all filter dropdowns
async function onChartDataChange() {
  const dataSource = document.getElementById('charts-data').value;
  
  console.log(`📊 Charts data source changed to: ${dataSource}`);
  
  try {
    // Load data for new data source
    const data = await dataLoader.getData(dataSource);
    
    // Immediately populate all filters (Supertrend + Sector + Industry)
    await filtersManager.populateChartFilters(dataSource, data);
    
    // Load charts with new data source
    await loadCharts();
  } catch (error) {
    console.error('❌ Error changing data source:', error);
  }
}

// ═══════════════════════════════════════════════════════════
// SYMBOLS TAB
// ═══════════════════════════════════════════════════════════

async function loadSymbolsTab() {
  console.log('📈 Loading symbols tab...');
  
  if (!symbolsTabInitialized) {
    await initializeSymbolsTab();
    symbolsTabInitialized = true;
  }
}

async function initializeSymbolsTab() {
  try {
    // Load default timeframe data (daily)
    const timeframe = document.getElementById('symbols-timeframe').value;
    const data = await dataLoader.getData(timeframe);
    
    // Populate supertrend dropdown with hardcoded values
    populateSymbolSupertrendDropdown(timeframe);
    
    // Populate symbol dropdown with all unique symbols
    populateSymbolDropdown(data);
    
    console.log('✓ Symbols tab initialized');
    
  } catch (error) {
    console.error('❌ Error initializing symbols tab:', error);
    alert('Error initializing symbols tab: ' + error.message);
  }
}

function populateSymbolDropdown(data) {
  const symbolSelect = document.getElementById('symbols-select');
  
  // Get unique symbols sorted alphabetically
  const symbols = [...new Set(data.map(row => row.trading_symbol))].sort();
  
  console.log(`Found ${symbols.length} unique symbols`);
  
  // Populate dropdown
  symbolSelect.innerHTML = '<option value="">-- Select a symbol --</option>' +
    symbols.map(symbol => `<option value="${symbol}">${symbol}</option>`).join('');
}

function populateSymbolSupertrendDropdown(timeframe) {
  const supertrendSelect = document.getElementById('symbols-supertrend');
  
  // Use hardcoded configs from filtersManager
  const configs = filtersManager.supertrendConfigs[timeframe];
  
  console.log('Populating symbol supertrend (hardcoded) for:', timeframe);
  
  supertrendSelect.innerHTML = configs.map(config => 
    `<option value="${config.id}">${config.label}</option>`
  ).join('');
}

async function onSymbolTimeframeChange() {
  const timeframe = document.getElementById('symbols-timeframe').value;
  
  console.log(`📈 Symbol timeframe changed to: ${timeframe}`);
  
  try {
    // Load data for new timeframe
    const data = await dataLoader.getData(timeframe);
    
    // Immediately update hardcoded supertrend dropdown
    populateSymbolSupertrendDropdown(timeframe);
    
    // Update symbol dropdown
    populateSymbolDropdown(data);
    
    // Clear current chart
    document.getElementById('symbols-content').style.display = 'none';
    document.getElementById('symbols-empty').style.display = 'block';
    document.getElementById('symbols-select').value = '';
    
  } catch (error) {
    console.error('❌ Error changing timeframe:', error);
    alert('Error loading data: ' + error.message);
  }
}

async function loadSymbolChart() {
  const symbol = document.getElementById('symbols-select').value;
  
  if (!symbol) {
    document.getElementById('symbols-content').style.display = 'none';
    document.getElementById('symbols-empty').style.display = 'block';
    return;
  }
  
  console.log(`📈 Loading chart for ${symbol}...`);
  
  try {
    document.getElementById('symbols-loading').style.display = 'block';
    document.getElementById('symbols-content').style.display = 'none';
    document.getElementById('symbols-empty').style.display = 'none';
    
    // Get selected timeframe and supertrend
    const timeframe = document.getElementById('symbols-timeframe').value;
    const supertrendConfig = document.getElementById('symbols-supertrend').value;
    
    // Load data
    const data = await dataLoader.getData(timeframe);
    
    // Get candles for this symbol
    const candles = dataLoader.getSymbolCandles(data, symbol);
    
    if (candles.length === 0) {
      alert(`No data found for ${symbol}`);
      document.getElementById('symbols-loading').style.display = 'none';
      document.getElementById('symbols-empty').style.display = 'block';
      return;
    }
    
    // Get latest candle for direction badge
    const latestCandle = candles[candles.length - 1];
    const directionCol = `direction_${supertrendConfig}`;
    const direction = latestCandle[directionCol];
    
    // Update chart title and badge
    document.getElementById('symbols-chart-title').textContent = symbol;
    const badge = document.getElementById('symbols-chart-badge');
    if (direction === -1) {
      badge.textContent = 'Long';
      badge.className = 'chart-type-badge long';
      badge.style.display = 'inline-block';
    } else if (direction === 1) {
      badge.textContent = 'Short';
      badge.className = 'chart-type-badge short';
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
    
    // Render chart
    chartRenderer.renderChart('symbols-chart', symbol, candles, supertrendConfig, direction);
    
    // Show content
    document.getElementById('symbols-loading').style.display = 'none';
    document.getElementById('symbols-content').style.display = 'block';
    
    console.log(`✓ Chart loaded for ${symbol}`);
    
  } catch (error) {
    console.error('❌ Error loading symbol chart:', error);
    alert('Error loading chart: ' + error.message);
    document.getElementById('symbols-loading').style.display = 'none';
    document.getElementById('symbols-empty').style.display = 'block';
  }
}

// ═══════════════════════════════════════════════════════════
// TABLE RENDERING
// ═══════════════════════════════════════════════════════════

function renderSignalsTable(tbodyId, signals, sheet, supertrend) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = '';
  
  if (!signals.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-secondary);">No signals found</td></tr>';
    return;
  }
  
  signals.forEach(signal => {
    const type = signal.direction === -1 ? 'Long' : 'Short';
    const isInWatchlist = checkIfInWatchlist(signal.symbol, sheet, supertrend, type);
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="checkbox-cell">
        <input type="checkbox" ${isInWatchlist ? 'checked' : ''} 
               onchange="toggleWatchlist(this, '${signal.symbol}', '${sheet}', '${supertrend}', '${type}', '${signal.pctDiff}', '${signal.flatbase}')">
      </td>
      <td><strong>${signal.symbol}</strong></td>
      <td>${signal.close}</td>
      <td class="${signal.ltpPercent >= 0 ? 'positive' : 'negative'}">${signal.ltpPercent}%</td>
      <td>${signal.pctDiff}</td>
      <td>${signal.flatbase}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ═══════════════════════════════════════════════════════════
// WATCHLIST MANAGEMENT (Using existing Apps Script)
// ═══════════════════════════════════════════════════════════

async function loadWatchlist() {
  console.log('📋 Loading watchlist...');
  
  try {
    document.getElementById('watchlist-loading').style.display = 'block';
    document.getElementById('watchlist-content').style.display = 'none';
    
    const response = await fetch(`${CONFIG.APPS_SCRIPT_URL}?action=getWatchlist`);
    const data = await response.json();
    watchlistData = data;
    
    renderWatchlist();
    
    document.getElementById('watchlist-last-updated').textContent = 
      `Updated: ${new Date().toLocaleTimeString()}`;
    
  } catch (error) {
    console.error('❌ Error loading watchlist:', error);
  }
}

async function loadWatchlistSilent() {
  try {
    const response = await fetch(`${CONFIG.APPS_SCRIPT_URL}?action=getWatchlist`);
    const data = await response.json();
    watchlistData = data;
  } catch (error) {
    console.error('❌ Error loading watchlist:', error);
  }
}

function renderWatchlist() {
  document.getElementById('watchlist-loading').style.display = 'none';
  document.getElementById('watchlist-content').style.display = 'block';
  
  const tbody = document.getElementById('watchlist-tbody');
  tbody.innerHTML = '';
  
  if (!watchlistData.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 40px; color: var(--text-secondary);">No items in watchlist</td></tr>';
    return;
  }
  
  watchlistData.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="checkbox-cell">
        <input type="checkbox" checked 
               onchange="removeFromWatchlistUI(this, '${item.symbol}', '${item.sheet}', '${item.supertrend}', '${item.type}')">
      </td>
      <td><strong>${item.symbol}</strong></td>
      <td>${item.sheet}</td>
      <td>${item.supertrend}</td>
      <td>${item.type}</td>
      <td>${item.pct}</td>
      <td>${item.flatbase}</td>
      <td>${item.dateAdded ? new Date(item.dateAdded).toLocaleDateString() : ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

function checkIfInWatchlist(symbol, sheet, supertrend, type) {
  return watchlistData.some(item => 
    item.symbol === symbol && 
    item.sheet === sheet && 
    item.supertrend === supertrend && 
    item.type === type
  );
}

async function toggleWatchlist(checkbox, symbol, sheet, supertrend, type, pct, flatbase) {
  if (checkbox.checked) {
    await addToWatchlist(symbol, sheet, supertrend, type, pct, flatbase);
  } else {
    await removeFromWatchlist(symbol, sheet, supertrend, type);
  }
}

async function removeFromWatchlistUI(checkbox, symbol, sheet, supertrend, type) {
  if (!checkbox.checked) {
    await removeFromWatchlist(symbol, sheet, supertrend, type);
    setTimeout(() => {
      loadWatchlist();
      if (currentTab === 'daily') loadDailySignals();
      if (currentTab === '125min') load125minSignals();
    }, 500);
  }
}

async function addToWatchlist(symbol, sheet, supertrend, type, pct, flatbase) {
  try {
    const url = `${CONFIG.APPS_SCRIPT_URL}?action=addToWatchlist&symbol=${encodeURIComponent(symbol)}&sheet=${encodeURIComponent(sheet)}&supertrend=${encodeURIComponent(supertrend)}&type=${encodeURIComponent(type)}&pct=${pct}&flatbase=${flatbase}`;
    await fetch(url);
    setTimeout(() => loadWatchlistSilent(), 500);
    console.log('✅ Added to watchlist:', symbol);
  } catch (error) {
    console.error('❌ Error adding:', error);
  }
}

async function removeFromWatchlist(symbol, sheet, supertrend, type) {
  try {
    const url = `${CONFIG.APPS_SCRIPT_URL}?action=removeFromWatchlist&symbol=${encodeURIComponent(symbol)}&sheet=${encodeURIComponent(sheet)}&supertrend=${encodeURIComponent(supertrend)}&type=${encodeURIComponent(type)}`;
    await fetch(url);
    setTimeout(() => loadWatchlistSilent(), 500);
    console.log('✅ Removed from watchlist:', symbol);
  } catch (error) {
    console.error('❌ Error removing:', error);
  }
}

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

window.onload = function() {
  console.log('🚀 Signal Tracker initialized');
  initTheme();
  
  // Check if Supabase URL is configured
  if (CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL_HERE') {
    alert('⚠️ Please configure your SUPABASE_URL in js/config.js');
    return;
  }
  
  // Load initial tab
  loadDailySignals();
};