/**
 * Filters Module - VS and VB Signal Detection
 */

class FiltersManager {
  constructor() {
    this.selectedSymbols = new Set(); // Track selected symbols via checkboxes
  }

  /**
   * Detect Volatility Support (VS) signals
   * 
   * Logic:
   * 1. Latest candle has direction_ST_125m_sma15 === -1 (larger ATR bullish)
   * 2. abs(pct_diff_close_lowerband_ST_125m_sma3) <= pctDiff filter
   * 
   * @param {number} pctDiffFilter - User-defined pct diff threshold
   * @returns {Array} Array of VS signals
   */
  detectVolatilitySupport(pctDiffFilter) {
    console.log('=== DETECTING VOLATILITY SUPPORT (VS) ===');
    console.log('PctDiff Filter:', pctDiffFilter);
    
    const latestCandles = dataLoader.getLatestCandles();
    const signals = [];
    
    latestCandles.forEach((candle, symbol) => {
      // Filter 1: Larger ATR must be bullish (direction = -1)
      const directionLarger = candle[CONFIG.COLUMNS.DIRECTION_LARGER];
      if (directionLarger !== -1) return;
      
      // Filter 2: Absolute pct diff <= threshold
      const pctDiff = candle[CONFIG.COLUMNS.PCT_DIFF];
      if (pctDiff === null || pctDiff === undefined) return;
      
      const absPctDiff = Math.abs(pctDiff);
      if (absPctDiff > pctDiffFilter) return;
      
      // Signal found
      const close = candle[CONFIG.COLUMNS.CLOSE];
      
      signals.push({
        symbol: symbol,
        close: close ? close.toFixed(2) : 'N/A',
        pctDiff: absPctDiff.toFixed(2),
        timestamp: candle[CONFIG.COLUMNS.TIMESTAMP]
      });
    });
    
    // Sort by pctDiff ascending (closest to lowerband first)
    signals.sort((a, b) => parseFloat(a.pctDiff) - parseFloat(b.pctDiff));
    
    console.log('VS Signals found:', signals.length);
    return signals;
  }

  /**
   * Detect Volatility Breakout (VB) signals
   * 
   * Logic:
   * 1. Latest candle has both directions === -1 (both bullish)
   * 2. Check last 10 candles (including current): any close > upperBand_ST_125m_sma3
   * 
   * @returns {Array} Array of VB signals
   */
  detectVolatilityBreakout() {
    console.log('=== DETECTING VOLATILITY BREAKOUT (VB) ===');
    
    const dataBySymbol = dataLoader.getDataBySymbol();
    const signals = [];
    
    dataBySymbol.forEach((candles, symbol) => {
      if (candles.length === 0) return;
      
      // Get latest candle
      const latestCandle = candles[candles.length - 1];
      
      // Filter 1: Both supertrends must be bullish (direction = -1)
      const directionLarger = latestCandle[CONFIG.COLUMNS.DIRECTION_LARGER];
      const directionShorter = latestCandle[CONFIG.COLUMNS.DIRECTION_SHORTER];
      
      if (directionLarger !== -1 || directionShorter !== -1) return;
      
      // Filter 2: Check last 10 candles for breakout
      const last10Candles = candles.slice(-10); // Get last 10 candles (including current)
      
      let breakoutFound = false;
      for (const candle of last10Candles) {
        const close = candle[CONFIG.COLUMNS.CLOSE];
        const upperBand = candle[CONFIG.COLUMNS.UPPERBAND_SHORTER];
        
        if (close && upperBand && close > upperBand) {
          breakoutFound = true;
          break;
        }
      }
      
      if (!breakoutFound) return;
      
      // Signal found
      const close = latestCandle[CONFIG.COLUMNS.CLOSE];
      const lowerBand = latestCandle[CONFIG.COLUMNS.LOWERBAND_SHORTER];
      
      // Calculate pctDiff for sorting (not a filter, just for display/sorting)
      let pctDiff = 0;
      if (close && lowerBand) {
        pctDiff = Math.abs((close - lowerBand) / close * 100);
      }
      
      signals.push({
        symbol: symbol,
        close: close ? close.toFixed(2) : 'N/A',
        pctDiff: pctDiff.toFixed(2),
        timestamp: latestCandle[CONFIG.COLUMNS.TIMESTAMP]
      });
    });
    
    // Sort by pctDiff ascending
    signals.sort((a, b) => parseFloat(a.pctDiff) - parseFloat(b.pctDiff));
    
    console.log('VB Signals found:', signals.length);
    return signals;
  }

  /**
   * Toggle symbol selection
   * @param {string} symbol - Symbol to toggle
   */
  toggleSymbol(symbol) {
    if (this.selectedSymbols.has(symbol)) {
      this.selectedSymbols.delete(symbol);
    } else {
      this.selectedSymbols.add(symbol);
    }
    console.log('Selected symbols:', Array.from(this.selectedSymbols));
  }

  /**
   * Clear all selections
   */
  clearSelections() {
    this.selectedSymbols.clear();
    console.log('All selections cleared');
  }

  /**
   * Get selected symbols
   * @returns {Array<string>} Array of selected symbols
   */
  getSelectedSymbols() {
    return Array.from(this.selectedSymbols);
  }

  /**
   * Check if symbol is selected
   * @param {string} symbol
   * @returns {boolean}
   */
  isSelected(symbol) {
    return this.selectedSymbols.has(symbol);
  }
}

// Create global instance
const filtersManager = new FiltersManager();
console.log('✅ FiltersManager initialized');