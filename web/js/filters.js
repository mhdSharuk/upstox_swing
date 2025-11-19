/**
 * Filters Module - FIXED VERSION
 * Handles all filtering logic for signals and charts
 * FIX: Use correct column names that match Python backend (pct_diff_avg3_ instead of pct_diff_)
 */

class FiltersManager {
  constructor() {
    this.currentFilters = {
      daily: this.getDefaultFilters(),
      min125: this.getDefaultFilters(),
      charts: this.getDefaultChartFilters()
    };
  }

  /**
   * Get default filter values
   * @returns {Object} Default filter configuration
   */
  getDefaultFilters() {
    return {
      supertrend: '',
      sector: 'All',
      industry: 'All',
      mcap: 10000,
      pct: 2.5,
      flat: 3
    };
  }

  /**
   * Get default chart filter values
   * @returns {Object} Default chart filter configuration
   */
  getDefaultChartFilters() {
    return {
      data: 'daily',
      chartType: 'Long',
      from: 'filtered',
      supertrend: '',
      pctDiff: 2.5,
      flatbase: 3
    };
  }

  /**
   * Apply filters to data and get signals
   * @param {Array} data - Full dataset
   * @param {Object} filters - Filter configuration
   * @param {string} supertrendConfig - Selected supertrend ID
   * @returns {Object} { long: [], short: [] }
   */
  applyFilters(data, filters, supertrendConfig) {
    console.log('=== APPLYING FILTERS ===');
    console.log('Total rows in data:', data.length);
    console.log('Filters:', filters);
    console.log('Supertrend config:', supertrendConfig);
    
    // Get latest candle for each symbol
    const latestCandles = dataLoader.getLatestCandles(data);
    console.log('Latest candles map size:', latestCandles.size);
    
    const longSignals = [];
    const shortSignals = [];
    
    // Get column names for the selected supertrend
    // FIXED: Use pct_diff_avg3_ to match Python backend column names
    const directionCol = `direction_${supertrendConfig}`;
    const supertrendCol = `supertrend_${supertrendConfig}`;
    const pctCol = `pct_diff_avg3_${supertrendConfig}`; // ← FIXED: Python creates pct_diff_avg3_ and pct_diff_latest_
    const flatbaseCol = `flatbase_count_${supertrendConfig}`;
    
    console.log('Looking for columns:', { directionCol, supertrendCol, pctCol, flatbaseCol });
    
    let processedCount = 0;
    let skippedMissingColumns = 0;
    let skippedFilters = 0;
    
    latestCandles.forEach((row, symbol) => {
      processedCount++;
      
      // Debug first few rows
      if (processedCount <= 3) {
        console.log(`Row ${processedCount} (${symbol}):`, {
          direction: row[directionCol],
          supertrend: row[supertrendCol],
          pctDiff: row[pctCol],
          flatbase: row[flatbaseCol],
          sector: row.sector,
          industry: row.industry,
          market_cap: row.market_cap
        });
      }
      
      // Skip if required columns don't exist
      if (row[directionCol] === undefined || row[supertrendCol] === undefined) {
        skippedMissingColumns++;
        if (processedCount <= 3) {
          console.warn(`Skipping ${symbol}: missing columns`);
        }
        return;
      }

      // Apply filters
      if (!this.passesFilters(row, filters, pctCol, flatbaseCol)) {
        skippedFilters++;
        return;
      }

      // Determine signal type based on direction
      // FIXED: direction -1 = Long (below supertrend), direction 1 = Short (above supertrend)
      const direction = row[directionCol];
      const close = row.close;
      const supertrend = row[supertrendCol];
      const pctDiff = row[pctCol] || 0;
      const flatbase = row[flatbaseCol] || 0;
      
      // Calculate LTP % (percentage difference from supertrend)
      const ltpPercent = ((close - supertrend) / supertrend * 100).toFixed(2);
      
      const signal = {
        symbol: symbol,
        close: close.toFixed(2),
        ltpPercent: ltpPercent,
        pctDiff: pctDiff.toFixed(2),
        flatbase: flatbase,
        direction: direction,
        supertrend: supertrend.toFixed(2),
        sector: row.sector || 'N/A',
        industry: row.industry || 'N/A',
        marketCap: row.market_cap || 0
      };
      
      // FIXED: direction -1 = Long, direction 1 = Short
      if (direction === -1) {
        longSignals.push(signal);
      } else if (direction === 1) {
        shortSignals.push(signal);
      }
    });
    
    console.log('=== FILTER RESULTS ===');
    console.log('Processed:', processedCount);
    console.log('Skipped (missing columns):', skippedMissingColumns);
    console.log('Skipped (failed filters):', skippedFilters);
    console.log('Long signals:', longSignals.length);
    console.log('Short signals:', shortSignals.length);
    console.log('======================');
    
    // Sort both arrays by pctDiff in ascending order (smallest first)
    longSignals.sort((a, b) => Math.abs(parseFloat(a.pctDiff)) - Math.abs(parseFloat(b.pctDiff)));
    shortSignals.sort((a, b) => Math.abs(parseFloat(a.pctDiff)) - Math.abs(parseFloat(b.pctDiff)));
    
    return { long: longSignals, short: shortSignals };
  }

  /**
   * Check if a row passes all filter criteria
   * @param {Object} row - Data row
   * @param {Object} filters - Filter configuration
   * @param {string} pctCol - Percentage diff column name
   * @param {string} flatbaseCol - Flatbase column name
   * @returns {boolean} True if passes all filters
   */
  passesFilters(row, filters, pctCol, flatbaseCol) {
    // Sector filter
    if (filters.sector !== 'All' && row.sector !== filters.sector) {
      return false;
    }
    
    // Industry filter
    if (filters.industry !== 'All' && row.industry !== filters.industry) {
      return false;
    }
    
    // Market cap filter
    const marketCap = row.market_cap || 0;
    if (marketCap < filters.mcap) {
      return false;
    }
    
    // Percentage diff filter (less than or equal)
    const pctDiff = Math.abs(row[pctCol] || 0);
    if (pctDiff > filters.pct) {
      return false;
    }
    
    // Flatbase filter (greater than or equal)
    const flatbase = row[flatbaseCol] || 0;
    if (flatbase < filters.flat) {
      return false;
    }
    
    return true;
  }

  /**
   * Populate filter dropdowns with unique values from data
   * @param {string} timeframe - 'daily' or 'min125'
   * @param {Array} data - Dataset to extract values from
   */
  populateFilterDropdowns(timeframe, data) {
    console.log(`=== POPULATING FILTERS FOR ${timeframe} ===`);
    console.log('Data length:', data.length);
    
    const prefix = timeframe === 'daily' ? 'daily' : 'min125';
    
    // Populate supertrend dropdown
    const supertrendSelect = document.getElementById(`${prefix}-supertrend`);
    const configs = dataLoader.getSupertrendConfigs(timeframe);
    
    console.log('Supertrend configs:', configs);
    
    supertrendSelect.innerHTML = configs.map(config => 
      `<option value="${config.id}">${config.label}</option>`
    ).join('');
    
    // Set default selection
    if (configs.length > 0) {
      supertrendSelect.value = configs[0].id;
      this.currentFilters[timeframe].supertrend = configs[0].id;
      console.log('Set default supertrend:', configs[0].id);
    }
    
    // Populate sector dropdown
    const sectors = dataLoader.getUniqueValues(data, 'sector');
    console.log('Sectors found:', sectors.length);
    
    const sectorSelect = document.getElementById(`${prefix}-sector`);
    sectorSelect.innerHTML = '<option value="All">All</option>' + 
      sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');
    
    // Populate industry dropdown
    const industries = dataLoader.getUniqueValues(data, 'industry');
    console.log('Industries found:', industries.length);
    
    const industrySelect = document.getElementById(`${prefix}-industry`);
    industrySelect.innerHTML = '<option value="All">All</option>' + 
      industries.map(industry => `<option value="${industry}">${industry}</option>`).join('');
    
    console.log('=== FILTERS POPULATED ===');
  }

  /**
   * Populate chart filter dropdowns
   * @param {string} timeframe - Current selected data timeframe
   */
  populateChartFilters(timeframe) {
    const supertrendSelect = document.getElementById('charts-supertrend');
    const configs = dataLoader.getSupertrendConfigs(timeframe);
    
    supertrendSelect.innerHTML = configs.map(config => 
      `<option value="${config.id}">${config.label}</option>`
    ).join('');
    
    if (configs.length > 0) {
      supertrendSelect.value = configs[0].id;
      this.currentFilters.charts.supertrend = configs[0].id;
    }
  }

  /**
   * Get current filter values from UI
   * @param {string} tab - 'daily', 'min125', or 'charts'
   * @returns {Object} Current filter values
   */
  getCurrentFilters(tab) {
    const prefix = tab === 'charts' ? 'charts' : (tab === 'daily' ? 'daily' : 'min125');
    
    if (tab === 'charts') {
      return {
        data: document.getElementById('charts-data').value,
        chartType: document.getElementById('charts-type').value,
        from: document.getElementById('charts-from').value,
        supertrend: document.getElementById('charts-supertrend').value,
        pctDiff: parseFloat(document.getElementById('charts-pct').value),
        flatbase: parseInt(document.getElementById('charts-flat').value)
      };
    } else {
      return {
        supertrend: document.getElementById(`${prefix}-supertrend`).value,
        sector: document.getElementById(`${prefix}-sector`).value,
        industry: document.getElementById(`${prefix}-industry`).value,
        mcap: parseFloat(document.getElementById(`${prefix}-mcap`).value),
        pct: parseFloat(document.getElementById(`${prefix}-pct`).value),
        flat: parseInt(document.getElementById(`${prefix}-flat`).value)
      };
    }
  }

  /**
   * Filter symbols for charts based on chart filters
   * @param {Array} data - Full dataset
   * @param {Object} chartFilters - Chart filter configuration
   * @returns {Array} Filtered symbols matching criteria
   */
  filterSymbolsForCharts(data, chartFilters) {
    const latestCandles = dataLoader.getLatestCandles(data);
    const directionCol = `direction_${chartFilters.supertrend}`;
    const pctCol = `pct_diff_avg3_${chartFilters.supertrend}`; // ← FIXED: Use avg3 column
    const flatbaseCol = `flatbase_count_${chartFilters.supertrend}`;
    
    // Determine target direction based on chart type
    // FIXED: Long = -1, Short = 1
    const targetDirection = chartFilters.chartType === 'Long' ? -1 : 1;
    
    const filteredSymbols = [];
    
    latestCandles.forEach((row, symbol) => {
      // Check direction matches chart type
      if (row[directionCol] !== targetDirection) {
        return;
      }
      
      // Apply pct diff and flatbase filters
      const pctDiff = Math.abs(row[pctCol] || 0);
      const flatbase = row[flatbaseCol] || 0;
      
      if (pctDiff <= chartFilters.pctDiff && flatbase >= chartFilters.flatbase) {
        filteredSymbols.push({
          symbol: symbol,
          direction: targetDirection,
          row: row
        });
      }
    });
    
    return filteredSymbols;
  }
}

// Create global instance
const filtersManager = new FiltersManager();