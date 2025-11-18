/**
 * Filters Module
 * Handles all filtering logic for signals and charts
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
    // Get latest candle for each symbol
    const latestCandles = dataLoader.getLatestCandles(data);
    
    const longSignals = [];
    const shortSignals = [];
    
    // Get column names for the selected supertrend
    const directionCol = `direction_${supertrendConfig}`;
    const supertrendCol = `supertrend_${supertrendConfig}`;
    const pctCol = `pct_diff_${supertrendConfig}`;
    const flatbaseCol = `flatbase_count_${supertrendConfig}`;
    
    latestCandles.forEach((row, symbol) => {
      // Skip if required columns don't exist
      if (row[directionCol] === undefined || row[supertrendCol] === undefined) {
        return;
      }

      // Apply filters
      if (!this.passesFilters(row, filters, pctCol, flatbaseCol)) {
        return;
      }

      // Determine signal type based on direction
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
      
      if (direction === 1) {
        longSignals.push(signal);
      } else if (direction === -1) {
        shortSignals.push(signal);
      }
    });
    
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
    if (row.market_cap < filters.mcap) {
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
    const prefix = timeframe === 'daily' ? 'daily' : 'min125';
    
    // Populate supertrend dropdown
    const supertrendSelect = document.getElementById(`${prefix}-supertrend`);
    const configs = dataLoader.getSupertrendConfigs(timeframe);
    
    supertrendSelect.innerHTML = configs.map(config => 
      `<option value="${config.id}">${config.label}</option>`
    ).join('');
    
    // Set default selection
    if (configs.length > 0) {
      supertrendSelect.value = configs[0].id;
      this.currentFilters[timeframe].supertrend = configs[0].id;
    }
    
    // Populate sector dropdown
    const sectors = dataLoader.getUniqueValues(data, 'sector');
    const sectorSelect = document.getElementById(`${prefix}-sector`);
    sectorSelect.innerHTML = '<option value="All">All</option>' + 
      sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');
    
    // Populate industry dropdown
    const industries = dataLoader.getUniqueValues(data, 'industry');
    const industrySelect = document.getElementById(`${prefix}-industry`);
    industrySelect.innerHTML = '<option value="All">All</option>' + 
      industries.map(industry => `<option value="${industry}">${industry}</option>`).join('');
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
    const pctCol = `pct_diff_${chartFilters.supertrend}`;
    const flatbaseCol = `flatbase_count_${chartFilters.supertrend}`;
    
    // Determine target direction based on chart type
    const targetDirection = chartFilters.chartType === 'Long' ? 1 : -1;
    
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