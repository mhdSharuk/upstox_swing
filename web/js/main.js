/**
 * Main Application Module - Signal Tab & Charts Tab
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
  
  // Update charts theme if charts are rendered
  if (chartsManager && chartsManager.charts.size > 0) {
    chartsManager.updateChartsTheme();
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

function switchTab(tabName) {
  currentTab = tabName;
  
  // Update tab buttons
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  
  // Update tab content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(tabName + '-tab').classList.add('active');
  
  // Load data for the tab
  if (tabName === 'signals') {
    loadSignals();
  } else if (tabName === 'charts') {
    loadCharts();
  }
  // Watchlist tab is placeholder for now
}

// ═══════════════════════════════════════════════════════════
// SIGNALS TAB - MAIN FUNCTIONALITY
// ═══════════════════════════════════════════════════════════

/**
 * Load signals with current filter settings
 * @param {boolean} forceRefresh - Skip cache and reload from Supabase
 */
async function loadSignals(forceRefresh = false) {
  if (isLoading) {
    console.log('Already loading, skipping...');
    return;
  }
  
  isLoading = true;
  console.log('📡 Loading signals...', { forceRefresh });
  const startTime = performance.now();
  
  try {
    // Update UI - show loading
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
      refreshBtn.disabled = true;
      refreshBtn.innerHTML = forceRefresh ? '⏳ Refreshing...' : '⏳ Loading...';
    }
    
    document.getElementById('signals-loading').style.display = 'block';
    document.getElementById('signals-content').style.display = 'none';
    
    // Clear cache if force refresh
    if (forceRefresh) {
      await dataLoader.clearCache();
    }
    
    // Load data
    await dataLoader.getData(forceRefresh);
    
    // Get filter value
    const pctDiffFilter = parseFloat(document.getElementById('pctdiff-filter').value) || 2.5;
    console.log('Filter - PctDiff:', pctDiffFilter);
    
    // Detect signals
    const vsSignals = filtersManager.detectVolatilitySupport(pctDiffFilter);
    const vbSignals = filtersManager.detectVolatilityBreakout();
    
    // Render tables
    renderSignalTable('vs-tbody', vsSignals, 'vs-count');
    renderSignalTable('vb-tbody', vbSignals, 'vb-count');
    
    // Show content
    document.getElementById('signals-loading').style.display = 'none';
    document.getElementById('signals-content').style.display = 'block';
    
    // Update last updated timestamp
    const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
    const now = new Date().toLocaleTimeString();
    document.getElementById('last-updated').textContent = `Last updated: ${now} (${elapsed}s)`;
    
    // Re-enable refresh button
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.innerHTML = '🔄 Refresh';
    }
    
    console.log(`✓ Signals loaded in ${elapsed}s`);
    console.log('VS:', vsSignals.length, 'VB:', vbSignals.length);
    
  } catch (error) {
    console.error('❌ Error loading signals:', error);
    alert('Error loading signals: ' + error.message);
    
    document.getElementById('signals-loading').style.display = 'none';
    
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
      refreshBtn.disabled = false;
      refreshBtn.innerHTML = '🔄 Refresh';
    }
  } finally {
    isLoading = false;
  }
}

/**
 * Render signal table
 * @param {string} tbodyId - Table body element ID
 * @param {Array} signals - Array of signal objects
 * @param {string} countId - Count element ID
 */
function renderSignalTable(tbodyId, signals, countId) {
  const tbody = document.getElementById(tbodyId);
  const countEl = document.getElementById(countId);
  
  // Update count
  countEl.textContent = signals.length;
  
  // Clear table
  tbody.innerHTML = '';
  
  if (signals.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 40px; color: var(--text-secondary);">No signals found</td></tr>';
    return;
  }
  
  // Render rows
  signals.forEach(signal => {
    const isSelected = filtersManager.isSelected(signal.symbol);
    
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="width: 40px;">
        <input 
          type="checkbox" 
          class="symbol-checkbox" 
          data-symbol="${signal.symbol}"
          ${isSelected ? 'checked' : ''}
        >
      </td>
      <td><strong>${signal.symbol}</strong></td>
      <td>${signal.close}</td>
    `;
    tbody.appendChild(tr);
  });
  
  // Attach checkbox event listeners
  document.querySelectorAll('.symbol-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const symbol = e.target.dataset.symbol;
      filtersManager.toggleSymbol(symbol);
    });
  });
}

/**
 * Handle filter change (auto-update on input)
 */
function onFilterChange() {
  if (!dataLoader.data) {
    console.log('No data loaded yet, skipping filter update');
    return;
  }
  
  console.log('Filter changed, updating signals...');
  
  // Get filter value
  const pctDiffFilter = parseFloat(document.getElementById('pctdiff-filter').value) || 2.5;
  
  // Re-detect signals with new filter
  const vsSignals = filtersManager.detectVolatilitySupport(pctDiffFilter);
  const vbSignals = filtersManager.detectVolatilityBreakout();
  
  // Re-render tables
  renderSignalTable('vs-tbody', vsSignals, 'vs-count');
  renderSignalTable('vb-tbody', vbSignals, 'vb-count');
  
  console.log('Signals updated with new filter');
}

// ═══════════════════════════════════════════════════════════
// CHARTS TAB - FUNCTIONALITY
// ═══════════════════════════════════════════════════════════

/**
 * Load charts for the current strategy
 */
async function loadCharts() {
  console.log('📈 Loading charts tab...');
  
  try {
    // Ensure data is loaded
    if (!dataLoader.data) {
      await dataLoader.getData();
    }
    
    // Get current strategy selection
    const strategy = document.getElementById('strategy-filter').value;
    
    // Render charts
    await chartsManager.renderCharts(strategy);
    
  } catch (error) {
    console.error('❌ Error loading charts:', error);
    alert('Error loading charts: ' + error.message);
  }
}

/**
 * Handle strategy change
 */
function onStrategyChange() {
  const strategy = document.getElementById('strategy-filter').value;
  console.log('Strategy changed to:', strategy);
  
  // Re-render charts with new strategy
  chartsManager.renderCharts(strategy);
}

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 App initialized');
  
  // Verify dependencies
  if (typeof CONFIG === 'undefined') {
    console.error('❌ CONFIG not loaded! Ensure config.js is included.');
    alert('Configuration error. Check console for details.');
    return;
  }
  if (typeof dataLoader === 'undefined') {
    console.error('❌ dataLoader not loaded! Ensure dataLoader.js is included.');
    alert('DataLoader error. Check console for details.');
    return;
  }
  if (typeof filtersManager === 'undefined') {
    console.error('❌ filtersManager not loaded! Ensure filters.js is included.');
    alert('FiltersManager error. Check console for details.');
    return;
  }
  if (typeof chartsManager === 'undefined') {
    console.error('❌ chartsManager not loaded! Ensure chartsManager.js is included.');
    alert('ChartsManager error. Check console for details.');
    return;
  }
  
  console.log('✅ All dependencies loaded');
  
  // Initialize theme
  initTheme();
  
  // Load signals automatically
  loadSignals();
});