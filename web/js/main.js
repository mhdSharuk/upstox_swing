/**
 * Main Application Module
 * UPDATED: New Signals tab with strategy-based signal detection
 */

// Global state
let currentTab = 'signals';
let isLoading = false;

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
  if (typeof chartRenderer !== 'undefined') {
    chartRenderer.updateChartsTheme();
  }
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
  if (tab === 'signals') {
    loadSignals();
  } else if (tab === 'charts') {
    loadChartsTab();
  } else if (tab === 'watchlist') {
    loadWatchlist();
  }
}

// ═══════════════════════════════════════════════════════════
// SIGNALS TAB (NEW)
// ═══════════════════════════════════════════════════════════

async function loadSignals(forceRefresh = false) {
  if (isLoading) return;
  isLoading = true;
  
  console.log('📡 Loading signals...');
  const startTime = performance.now();
  
  try {
    // Check if filtersManager exists
    if (typeof filtersManager === 'undefined' || !filtersManager) {
      throw new Error('FiltersManager not initialized. Check browser console for errors in filters.js');
    }
    
    if (typeof filtersManager.detectSignals !== 'function') {
      throw new Error('FiltersManager.detectSignals is not a function. FiltersManager object: ' + JSON.stringify(Object.keys(filtersManager)));
    }
    
    // Disable button and show loading
    const refreshBtn = document.getElementById('signals-refresh-btn');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.textContent = forceRefresh ? '⏳ Refreshing...' : '⏳ Loading...';
    }
    
    document.getElementById('signals-loading').style.display = 'block';
    document.getElementById('signals-content').style.display = 'none';
    
    // Get filter values
    const timeframe = document.getElementById('signals-timeframe').value;
    const strategy = document.getElementById('signals-strategy').value;
    const mcap = parseFloat(document.getElementById('signals-mcap').value) || 10000;
    const pctDiff = parseFloat(document.getElementById('signals-pctdiff').value) || 2.5;
    
    console.log('Filters:', { timeframe, strategy, mcap, pctDiff });
    
    // Clear cache if force refresh
    if (forceRefresh) {
      await dataLoader.clearCache();
      dataLoader.dailyData = null;
      dataLoader.min125Data = null;
      dataLoader.min60Data = null;
    }
    
    // Load data for selected timeframe
    const data = await dataLoader.getData(timeframe);
    
    // Detect signals using new strategy logic
    const signals = filtersManager.detectSignals(data, {
      timeframe,
      strategy,
      mcap,
      pctDiff
    });
    
    // Render signals table
    renderSignalsTable(signals);
    
    // Update count
    document.getElementById('signals-count').textContent = signals.length;
    
    // Show content
    document.getElementById('signals-loading').style.display = 'none';
    document.getElementById('signals-content').style.display = 'block';
    
    // Update last updated
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    document.getElementById('signals-last-updated').textContent = 
      `Updated: ${new Date().toLocaleTimeString()} (${elapsed}s)`;
    
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.textContent = '🔄 Refresh';
    }
    
    console.log(`✓ Signals loaded in ${elapsed}s`);
    
  } catch (error) {
    console.error('❌ Error loading signals:', error);
    alert('Error loading signals: ' + error.message);
    
    document.getElementById('signals-loading').style.display = 'none';
    const refreshBtn = document.getElementById('signals-refresh-btn');
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.textContent = '🔄 Refresh';
    }
  } finally {
    isLoading = false;
  }
}

function renderSignalsTable(signals) {
  const tbody = document.getElementById('signals-tbody');
  tbody.innerHTML = '';
  
  if (signals.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-secondary);">No signals found</td></tr>';
    return;
  }
  
  signals.forEach(signal => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${signal.symbol}</strong></td>
      <td>${signal.close}</td>
      <td class="${signal.ltpPercent >= 0 ? 'positive' : 'negative'}">${signal.ltpPercent}%</td>
      <td>${signal.pctDiff}%</td>
      <td>${signal.sector}</td>
      <td>${signal.industry}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ═══════════════════════════════════════════════════════════
// CHARTS TAB
// ═══════════════════════════════════════════════════════════

async function loadChartsTab() {
  console.log('📊 Loading charts tab...');
  
  const dataSource = document.getElementById('charts-data').value || 'daily';
  const data = await dataLoader.getData(dataSource);
  
  await filtersManager.populateChartFilters(dataSource, data);
  await loadCharts();
}

async function loadCharts() {
  console.log('📊 Loading charts...');
  const startTime = performance.now();
  
  try {
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-content').style.display = 'none';
    
    const chartFilters = filtersManager.getCurrentFilters('charts');
    const timeframe = chartFilters.data;
    const data = await dataLoader.getData(timeframe);
    
    const filteredSymbols = filtersManager.filterSymbolsForCharts(data, chartFilters);
    
    console.log(`Found ${filteredSymbols.length} symbols matching filters`);
    
    if (typeof chartRenderer !== 'undefined') {
      await chartRenderer.renderChartsGrid(filteredSymbols, chartFilters.supertrend, timeframe);
    }
    
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

async function onChartDataChange() {
  const dataSource = document.getElementById('charts-data').value;
  console.log(`📊 Chart data changed to: ${dataSource}`);
  
  try {
    const data = await dataLoader.getData(dataSource);
    await filtersManager.populateChartFilters(dataSource, data);
    await loadCharts();
  } catch (error) {
    console.error('❌ Error changing chart data:', error);
    alert('Error loading data: ' + error.message);
  }
}

// ═══════════════════════════════════════════════════════════
// WATCHLIST TAB
// ═══════════════════════════════════════════════════════════

let watchlistData = [];

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
    alert('Error loading watchlist: ' + error.message);
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
      <td><strong>${item.symbol}</strong></td>
      <td>${item.sheet || 'N/A'}</td>
      <td>${item.supertrend || 'N/A'}</td>
      <td>${item.type || 'N/A'}</td>
      <td>${item.pct || 'N/A'}</td>
      <td>${item.flatbase || 'N/A'}</td>
      <td>${item.dateAdded || 'N/A'}</td>
      <td><button class="remove-btn" onclick="removeFromWatchlist('${item.symbol}')">Remove</button></td>
    `;
    tbody.appendChild(tr);
  });
}

async function removeFromWatchlist(symbol) {
  try {
    const response = await fetch(CONFIG.APPS_SCRIPT_URL, {
      method: 'POST',
      body: JSON.stringify({ action: 'remove', symbol })
    });
    
    if (response.ok) {
      await loadWatchlist();
    }
  } catch (error) {
    console.error('Error removing from watchlist:', error);
    alert('Error removing from watchlist');
  }
}

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 App initialized');
  
  // Verify required objects are loaded
  if (typeof CONFIG === 'undefined') {
    console.error('❌ CONFIG not loaded! Ensure config.js is included before main.js');
    return;
  }
  if (typeof dataLoader === 'undefined') {
    console.error('❌ dataLoader not loaded! Ensure dataLoader.js is included before main.js');
    return;
  }
  if (typeof filtersManager === 'undefined') {
    console.error('❌ filtersManager not loaded! Ensure filters.js is included before main.js');
    return;
  }
  
  console.log('✅ All dependencies loaded');
  initTheme();
  loadSignals(); // Load signals tab by default
});