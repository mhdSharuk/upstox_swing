/* ═══════════════════════════════════════════════════════════
   UI RENDERING & MANIPULATION
   
   Handles all DOM manipulation and UI updates
   ═══════════════════════════════════════════════════════════ */

const UI = {
  /**
   * Populate a select dropdown with options
   * @param {string} id - Select element ID
   * @param {Array} options - Options to populate
   * @param {string} defaultValue - Default selected value
   */
  populateSelect(id, options, defaultValue) {
    const select = document.getElementById(id);
    select.innerHTML = '';

    options.forEach(opt => {
      const option = document.createElement('option');
      option.value = opt;
      option.textContent = opt;
      if (opt === defaultValue) option.selected = true;
      select.appendChild(option);
    });
  },

  /**
   * Set loading state for a tab
   * @param {string} prefix - Tab prefix (daily, min125, watchlist)
   * @param {boolean} isLoading - Loading state
   */
  setLoading(prefix, isLoading) {
    const loadingEl = document.getElementById(`${prefix}-loading`);
    const contentEl = document.getElementById(`${prefix}-content`);
    const refreshBtn = document.getElementById(`${prefix}-refresh-btn`);

    if (isLoading) {
      loadingEl.style.display = 'block';
      contentEl.style.display = 'none';
      refreshBtn.disabled = true;
      refreshBtn.textContent = '⏳ Loading...';
    } else {
      loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
      refreshBtn.disabled = false;
      refreshBtn.textContent = '🔄 Refresh';
    }
  },

  /**
   * Update timestamp display
   * @param {string} prefix - Tab prefix
   * @param {number} loadTime - Load time in milliseconds
   */
  updateTimestamp(prefix, loadTime) {
    const timestampEl = document.getElementById(`${prefix}-last-updated`);
    timestampEl.textContent = `Updated ${new Date().toLocaleTimeString()} (${loadTime}ms)`;
  },

  /**
   * Render signals tables
   * @param {string} prefix - Tab prefix (daily, min125)
   * @param {Array} longSignals - Long signals data
   * @param {Array} shortSignals - Short signals data
   * @param {string} sheetName - Sheet name
   */
  renderSignals(prefix, longSignals, shortSignals, sheetName) {
    this.renderSignalTable(`${prefix}-long`, longSignals, sheetName, 'Long');
    this.renderSignalTable(`${prefix}-short`, shortSignals, sheetName, 'Short');

    // Update counts
    document.getElementById(`${prefix}-long-count`).textContent = longSignals.length;
    document.getElementById(`${prefix}-short-count`).textContent = shortSignals.length;
  },

  /**
   * Render a single signal table
   * @param {string} prefix - Table prefix (daily-long, daily-short, etc.)
   * @param {Array} data - Signal data
   * @param {string} sheetName - Sheet name
   * @param {string} signalType - Signal type (Long/Short)
   */
  renderSignalTable(prefix, data, sheetName, signalType) {
    const tbody = document.getElementById(`${prefix}-tbody`);
    tbody.innerHTML = '';

    if (!data || !data.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; padding: 20px; color: var(--text-secondary);">
            No signals found
          </td>
        </tr>
      `;
      return;
    }

    data.forEach(row => {
      const isInWatchlist = WatchlistManager.checkExists(
        row.symbol,
        sheetName,
        row.supertrend,
        signalType
      );

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="checkbox-cell">
          <input type="checkbox" 
                 ${isInWatchlist ? 'checked' : ''} 
                 onchange="toggleWatchlist(this, '${row.symbol}', '${sheetName}', '${row.supertrend}', '${signalType}', ${row.pct}, ${row.flatbase})">
        </td>
        <td><strong>${row.symbol}</strong></td>
        <td>${Number(row.close).toFixed(2)}</td>
        <td class="${row.ltp >= 0 ? 'positive' : 'negative'}">${row.ltp}%</td>
        <td>${Number(row.pct).toFixed(2)}</td>
        <td>${row.flatbase}</td>
      `;
      tbody.appendChild(tr);
    });
  },

  /**
   * Render watchlist table
   * @param {Array} data - Watchlist data
   */
  renderWatchlist(data) {
    const tbody = document.getElementById('watchlist-tbody');
    tbody.innerHTML = '';

    if (!data || !data.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 40px; color: var(--text-secondary);">
            No items in watchlist
          </td>
        </tr>
      `;
      return;
    }

    data.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="checkbox-cell">
          <input type="checkbox" 
                 checked 
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
  },

  /**
   * Get filter values for a specific tab
   * @param {string} prefix - Tab prefix (daily, min125)
   * @returns {Object} Filter values
   */
  getFilters(prefix) {
    return {
      supertrend: document.getElementById(`${prefix}-supertrend`).value || '',
      sector: document.getElementById(`${prefix}-sector`).value || 'All',
      industry: document.getElementById(`${prefix}-industry`).value || 'All',
      mcap: document.getElementById(`${prefix}-mcap`).value || CONFIG.DEFAULT_FILTERS.mcap,
      pct: document.getElementById(`${prefix}-pct`).value || CONFIG.DEFAULT_FILTERS.pct,
      flat: document.getElementById(`${prefix}-flat`).value || CONFIG.DEFAULT_FILTERS.flat
    };
  },

  /**
   * Check if filters are initialized
   * @param {string} prefix - Tab prefix
   * @returns {boolean}
   */
  areFiltersInitialized(prefix) {
    return !!document.getElementById(`${prefix}-supertrend`).value;
  },

  /**
   * Initialize filter dropdowns
   * @param {string} prefix - Tab prefix
   * @param {Object} data - Data containing filter options
   */
  initializeFilters(prefix, data) {
    this.populateSelect(`${prefix}-supertrend`, data.supertrends, data.supertrends[0]);
    this.populateSelect(`${prefix}-sector`, data.sectors, 'All');
    this.populateSelect(`${prefix}-industry`, data.industries, 'All');
  }
};