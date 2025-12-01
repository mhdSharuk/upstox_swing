/**
 * Filters Module - UPDATED with New Signal Detection Strategies
 * Implements Volatility Breakout and Volatility Support strategies
 */

class FiltersManager {
  constructor() {
    this.currentFilters = {
      signals: {
        timeframe: 'daily',
        strategy: 'volatility_breakout',
        mcap: 10000,
        pctDiff: 2.5
      },
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
   * Get current filters for a tab
   * @param {string} tab - Tab name
   * @returns {Object} Current filters
   */
  getCurrentFilters(tab) {
    return this.currentFilters[tab];
  }

  /**
   * MAIN METHOD: Detect signals based on strategy
   * @param {Array} data - Full dataset
   * @param {Object} filters - Filter configuration {timeframe, strategy, mcap, pctDiff}
   * @returns {Array} Array of signals
   */
  detectSignals(data, filters) {
    console.log('=== DETECTING SIGNALS ===');
    console.log('Filters:', filters);
    console.log('Data rows:', data.length);
    
    const { timeframe, strategy, mcap, pctDiff } = filters;
    
    // Get strategy config for this timeframe
    let timeframeKey;
    if (timeframe === 'daily') {
      timeframeKey = 'daily';
    } else if (timeframe === 'min125') {
      timeframeKey = 'min125';
    } else if (timeframe === 'min60') {
      timeframeKey = 'min60';
    }
    
    const strategyConfig = CONFIG.STRATEGY_CONFIGS[timeframeKey];
    if (!strategyConfig) {
      console.error('No strategy config for timeframe:', timeframeKey);
      return [];
    }
    
    const biggerST = strategyConfig.bigger;
    const shorterST = strategyConfig.shorter;
    
    console.log('Using supertrends:', { biggerST, shorterST });
    
    // Column names
    const biggerDirectionCol = `direction_${biggerST}`;
    const shorterDirectionCol = `direction_${shorterST}`;
    const shorterSupertrendCol = `supertrend_${shorterST}`;
    const shorterUpperbandCol = `upperBand_${shorterST}`;
    const shorterLowerbandCol = `lowerBand_${shorterST}`;
    
    const signals = [];
    
    // Group data by symbol
    const dataBySymbol = new Map();
    data.forEach(row => {
      const symbol = row.trading_symbol;
      if (!symbol) return;
      
      if (!dataBySymbol.has(symbol)) {
        dataBySymbol.set(symbol, []);
      }
      dataBySymbol.get(symbol).push(row);
    });
    
    console.log(`Processing ${dataBySymbol.size} symbols...`);
    
    let processedCount = 0;
    let signalsGenerated = 0;
    
    dataBySymbol.forEach((candles, symbol) => {
      processedCount++;
      
      // Sort candles by timestamp
      candles.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
      
      // Get latest candle
      const latestCandle = candles[candles.length - 1];
      
      // Apply market cap filter
      const marketCap = latestCandle.market_cap || 0;
      if (marketCap < mcap) {
        return;
      }
      
      // Check if required columns exist
      if (latestCandle[biggerDirectionCol] === undefined || 
          latestCandle[shorterDirectionCol] === undefined) {
        return;
      }
      
      // BASELINE CONDITION: Bigger ATR supertrend must be bullish (direction = -1)
      if (latestCandle[biggerDirectionCol] !== -1) {
        return;
      }
      
      let signalGenerated = false;
      
      // Apply strategy logic
      if (strategy === 'volatility_breakout') {
        signalGenerated = this.checkVolatilityBreakout(
          candles, latestCandle, shorterDirectionCol, shorterSupertrendCol, shorterUpperbandCol
        );
      } else if (strategy === 'volatility_support') {
        signalGenerated = this.checkVolatilitySupport(
          latestCandle, shorterLowerbandCol, pctDiff
        );
      }
      
      if (signalGenerated) {
        signalsGenerated++;
        
        const close = latestCandle.close;
        const supertrend = latestCandle[shorterSupertrendCol];
        const ltpPercent = ((close - supertrend) / supertrend * 100).toFixed(2);
        
        // Calculate pct diff for support strategy
        const lowerband = latestCandle[shorterLowerbandCol];
        const pctDiffValue = Math.abs((close - lowerband) / close * 100).toFixed(2);
        
        signals.push({
          symbol: symbol,
          close: close.toFixed(2),
          ltpPercent: ltpPercent,
          pctDiff: pctDiffValue,
          sector: latestCandle.sector || 'N/A',
          industry: latestCandle.industry || 'N/A',
          marketCap: marketCap,
          timestamp: latestCandle.timestamp
        });
      }
    });
    
    console.log('=== SIGNAL DETECTION RESULTS ===');
    console.log('Processed symbols:', processedCount);
    console.log('Signals generated:', signalsGenerated);
    console.log('================================');
    
    // Sort by pctDiff ascending
    signals.sort((a, b) => parseFloat(a.pctDiff) - parseFloat(b.pctDiff));
    
    return signals;
  }

  /**
   * Check Volatility Breakout strategy
   * @param {Array} candles - All candles for symbol (sorted by time)
   * @param {Object} latestCandle - Latest candle
   * @param {string} shorterDirectionCol - Shorter term direction column
   * @param {string} shorterSupertrendCol - Shorter term supertrend column
   * @param {string} shorterUpperbandCol - Shorter term upperband column
   * @returns {boolean} True if signal generated
   */
  checkVolatilityBreakout(candles, latestCandle, shorterDirectionCol, shorterSupertrendCol, shorterUpperbandCol) {
    // Get last 10 candles (including latest)
    const last10Candles = candles.slice(-10);
    
    // Check if ANY of the last 10 candles meets the condition:
    // - Both bigger and smaller supertrend direction is -1 (bullish)
    // - Price closed above shorter term upperband
    let breakoutFound = false;
    
    for (const candle of last10Candles) {
      const shorterDirection = candle[shorterDirectionCol];
      const close = candle.close;
      const upperband = candle[shorterUpperbandCol];
      
      // Check: both supertrends bullish AND closed above upperband
      if (shorterDirection === -1 && close > upperband) {
        breakoutFound = true;
        break;
      }
    }
    
    if (!breakoutFound) {
      return false;
    }
    
    // Check removal condition:
    // If latest candle closed below shorter term supertrend AND turned bearish
    const latestClose = latestCandle.close;
    const latestShorterST = latestCandle[shorterSupertrendCol];
    const latestShorterDirection = latestCandle[shorterDirectionCol];
    
    if (latestClose < latestShorterST && latestShorterDirection === 1) {
      // Stock should be removed
      return false;
    }
    
    return true;
  }

  /**
   * Check Volatility Support strategy
   * @param {Object} latestCandle - Latest candle
   * @param {string} shorterLowerbandCol - Shorter term lowerband column
   * @param {number} pctDiff - User-defined pct diff threshold
   * @returns {boolean} True if signal generated
   */
  checkVolatilitySupport(latestCandle, shorterLowerbandCol, pctDiff) {
    const close = latestCandle.close;
    const lowerband = latestCandle[shorterLowerbandCol];
    
    if (!lowerband || !close) {
      return false;
    }
    
    // Formula: abs((close - lowerband) / close) * 100 <= pctDiff
    const calculatedPctDiff = Math.abs((close - lowerband) / close) * 100;
    
    return calculatedPctDiff <= pctDiff;
  }

  /**
   * OLD METHOD: Apply filters to data and get signals (for legacy tabs)
   * @param {Array} data - Full dataset
   * @param {Object} filters - Filter configuration
   * @param {string} supertrendConfig - Selected supertrend ID
   * @returns {Object} { long: [], short: [] }
   */
  applyFilters(data, filters, supertrendConfig) {
    console.log('=== APPLYING FILTERS (LEGACY) ===');
    console.log('Total rows in data:', data.length);
    console.log('Filters:', filters);
    console.log('Supertrend config:', supertrendConfig);
    
    // Get latest candle for each symbol
    const latestCandles = dataLoader.getLatestCandles(data);
    console.log('Latest candles map size:', latestCandles.size);
    
    const longSignals = [];
    const shortSignals = [];
    
    // Get column names for the selected supertrend
    const directionCol = `direction_${supertrendConfig}`;
    const supertrendCol = `supertrend_${supertrendConfig}`;
    const pctCol = `pct_diff_avg3_${supertrendConfig}`;
    const flatbaseCol = `flatbase_count_${supertrendConfig}`;
    
    console.log('Looking for columns:', { directionCol, supertrendCol, pctCol, flatbaseCol });
    
    let processedCount = 0;
    let skippedMissingColumns = 0;
    let skippedFilters = 0;
    
    latestCandles.forEach((row, symbol) => {
      processedCount++;
      
      // Skip if required columns don't exist
      if (row[directionCol] === undefined || row[supertrendCol] === undefined) {
        skippedMissingColumns++;
        return;
      }

      // Apply filters
      if (!this.passesFilters(row, filters, pctCol, flatbaseCol)) {
        skippedFilters++;
        return;
      }

      // Determine signal type based on direction
      const direction = row[directionCol];
      const close = row.close;
      const supertrend = row[supertrendCol];
      const pctDiff = row[pctCol] || 0;
      const flatbase = row[flatbaseCol] || 0;
      
      // Calculate LTP %
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
    
    // Sort both arrays by pctDiff
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
    
    // Percentage diff filter
    const pctDiff = Math.abs(row[pctCol] || 0);
    if (pctDiff > filters.pct) {
      return false;
    }
    
    // Flatbase filter
    const flatbase = row[flatbaseCol] || 0;
    if (flatbase < filters.flat) {
      return false;
    }
    
    return true;
  }

  /**
   * Populate filter dropdowns with unique values from data
   * @param {string} timeframe - 'daily', 'min125', or 'min60'
   * @param {Array} data - Dataset to extract values from
   */
  populateFilterDropdowns(timeframe, data) {
    console.log(`=== POPULATING FILTERS FOR ${timeframe} ===`);
    
    const prefix = timeframe === 'daily' ? 'daily' : (timeframe === 'min60' ? 'min60' : 'min125');
    
    // Populate supertrend dropdown
    const supertrendSelect = document.getElementById(`${prefix}-supertrend`);
    if (supertrendSelect) {
      const configs = dataLoader.getSupertrendConfigs(timeframe);
      
      supertrendSelect.innerHTML = configs.map(config => 
        `<option value="${config.id}">${config.label}</option>`
      ).join('');
      
      if (configs.length > 0) {
        supertrendSelect.value = configs[0].id;
        this.currentFilters[timeframe].supertrend = configs[0].id;
      }
    }
    
    // Populate sector dropdown
    const sectors = dataLoader.getUniqueValues(data, 'sector');
    const sectorSelect = document.getElementById(`${prefix}-sector`);
    if (sectorSelect) {
      sectorSelect.innerHTML = '<option value="All">All</option>' + 
        sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');
    }
    
    // Populate industry dropdown
    const industries = dataLoader.getUniqueValues(data, 'industry');
    const industrySelect = document.getElementById(`${prefix}-industry`);
    if (industrySelect) {
      industrySelect.innerHTML = '<option value="All">All</option>' + 
        industries.map(industry => `<option value="${industry}">${industry}</option>`).join('');
    }
    
    console.log('Filters populated');
  }

  /**
   * Populate chart filters
   * @param {string} timeframe - 'daily', 'min125', or 'min60'
   * @param {Array} data - Dataset
   */
  async populateChartFilters(timeframe, data) {
    console.log(`=== POPULATING CHART FILTERS FOR ${timeframe} ===`);
    
    // Populate supertrend dropdown
    const supertrendSelect = document.getElementById('charts-supertrend');
    const configs = dataLoader.getSupertrendConfigs(timeframe);
    
    supertrendSelect.innerHTML = configs.map(config => 
      `<option value="${config.id}">${config.label}</option>`
    ).join('');
    
    if (configs.length > 0) {
      supertrendSelect.value = configs[0].id;
      this.currentFilters.charts.supertrend = configs[0].id;
    }
    
    // Populate sector dropdown
    const sectors = dataLoader.getUniqueValues(data, 'sector');
    const sectorSelect = document.getElementById('charts-sector');
    sectorSelect.innerHTML = '<option value="All">All</option>' + 
      sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');
    
    // Populate industry dropdown
    const industries = dataLoader.getUniqueValues(data, 'industry');
    const industrySelect = document.getElementById('charts-industry');
    industrySelect.innerHTML = '<option value="All">All</option>' + 
      industries.map(industry => `<option value="${industry}">${industry}</option>`).join('');
  }

  /**
   * Filter symbols for charts based on all chart filters
   * @param {Array} data - Full dataset
   * @param {Object} chartFilters - Chart filter configuration
   * @returns {Array} Filtered symbols with their data
   */
  filterSymbolsForCharts(data, chartFilters) {
    console.log('=== FILTERING SYMBOLS FOR CHARTS ===');
    console.log('Chart filters:', chartFilters);
    
    const latestCandles = dataLoader.getLatestCandles(data);
    const supertrendConfig = chartFilters.supertrend;
    const targetDirection = chartFilters.chartType === 'Long' ? -1 : 1;
    
    const directionCol = `direction_${supertrendConfig}`;
    const pctCol = `pct_diff_avg3_${supertrendConfig}`;
    const flatbaseCol = `flatbase_count_${supertrendConfig}`;
    
    const filteredSymbols = [];
    let processedCount = 0;
    let directionMatches = 0;
    let passedAllFilters = 0;
    
    latestCandles.forEach((row, symbol) => {
      processedCount++;
      
      // 1. Direction filter
      if (row[directionCol] !== targetDirection) {
        return;
      }
      directionMatches++;
      
      // 2. Sector filter
      if (chartFilters.sector !== 'All' && row.sector !== chartFilters.sector) {
        return;
      }
      
      // 3. Industry filter
      if (chartFilters.industry !== 'All' && row.industry !== chartFilters.industry) {
        return;
      }
      
      // 4. Market Cap filter
      const marketCap = row.market_cap || 0;
      if (marketCap < chartFilters.mcap) {
        return;
      }
      
      // 5. Pct Diff filter
      const pctDiff = Math.abs(row[pctCol] || 0);
      if (pctDiff > chartFilters.pctDiff) {
        return;
      }
      
      // 6. Flatbase filter
      const flatbase = row[flatbaseCol] || 0;
      if (flatbase < chartFilters.flatbase) {
        return;
      }
      
      passedAllFilters++;
      filteredSymbols.push({
        symbol: symbol,
        direction: targetDirection,
        row: row
      });
    });
    
    console.log('Charts filtering results:');
    console.log('  Processed:', processedCount);
    console.log('  Direction matches:', directionMatches);
    console.log('  Passed all filters:', passedAllFilters);
    
    // Sort by pctDiff ascending
    filteredSymbols.sort((a, b) => {
      const pctDiffA = Math.abs(a.row[pctCol] || 0);
      const pctDiffB = Math.abs(b.row[pctCol] || 0);
      return pctDiffA - pctDiffB;
    });
    
    return filteredSymbols;
  }
}

// Create global instance
let filtersManager;
try {
  filtersManager = new FiltersManager();
  console.log('✅ FiltersManager initialized successfully');
  console.log('  - detectSignals:', typeof filtersManager.detectSignals);
  console.log('  - applyFilters:', typeof filtersManager.applyFilters);
  console.log('  - getCurrentFilters:', typeof filtersManager.getCurrentFilters);
} catch (error) {
  console.error('❌ Error initializing FiltersManager:', error);
  console.error('Stack:', error.stack);
}