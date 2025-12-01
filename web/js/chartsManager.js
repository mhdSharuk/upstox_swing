/**
 * Charts Manager Module
 * Renders OHLC candles with larger/shorter supertrends and bands
 * Uses TradingView Lightweight Charts library
 */

class ChartsManager {
  constructor() {
    this.charts = new Map(); // Store chart instances
    this.currentStrategy = 'vs'; // Default strategy
  }

  /**
   * Render charts for selected strategy
   * @param {string} strategy - 'vs' or 'vb'
   */
  async renderCharts(strategy) {
    this.currentStrategy = strategy;
    
    console.log('📊 Rendering charts for strategy:', strategy);
    
    // Show loading
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-grid').innerHTML = '';
    
    // Clear existing charts
    this.clearAllCharts();
    
    try {
      // Ensure data is loaded
      if (!dataLoader.data) {
        await dataLoader.getData();
      }
      
      // Get filtered signals based on strategy
      let signals;
      if (strategy === 'vs') {
        const pctDiffFilter = parseFloat(document.getElementById('pctdiff-filter').value) || 2.5;
        signals = filtersManager.detectVolatilitySupport(pctDiffFilter);
      } else {
        signals = filtersManager.detectVolatilityBreakout();
      }
      
      console.log(`Found ${signals.length} symbols for ${strategy}`);
      
      if (signals.length === 0) {
        document.getElementById('charts-loading').style.display = 'none';
        document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No symbols found for this strategy</div>';
        return;
      }
      
      // Get data by symbol
      const dataBySymbol = dataLoader.getDataBySymbol();
      
      // Render charts for all symbols
      const chartsGrid = document.getElementById('charts-grid');
      
      signals.forEach((signal, index) => {
        const symbol = signal.symbol;
        const candles = dataBySymbol.get(symbol);
        
        if (!candles || candles.length === 0) {
          console.warn(`No data for ${symbol}`);
          return;
        }
        
        // Create chart container
        const chartWrapper = document.createElement('div');
        chartWrapper.className = 'chart-container';
        chartWrapper.innerHTML = `
          <div class="chart-header">
            <span class="chart-symbol">${symbol}</span>
            <span class="chart-info">₹${signal.close}</span>
          </div>
          <div class="chart-canvas" id="chart-${index}"></div>
        `;
        
        chartsGrid.appendChild(chartWrapper);
        
        // Render the chart
        setTimeout(() => {
          this.renderSingleChart(`chart-${index}`, symbol, candles);
        }, 50 * index); // Stagger rendering to prevent UI freeze
      });
      
      // Hide loading
      document.getElementById('charts-loading').style.display = 'none';
      
      console.log(`✓ Rendered ${signals.length} charts`);
      
    } catch (error) {
      console.error('❌ Error rendering charts:', error);
      document.getElementById('charts-loading').style.display = 'none';
      document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">Error loading charts</div>';
    }
  }

  /**
   * Render a single chart with OHLC + supertrends + bands
   * @param {string} containerId - DOM element ID
   * @param {string} symbol - Trading symbol
   * @param {Array} candles - Array of candle data
   */
  renderSingleChart(containerId, symbol, candles) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Get theme
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    const isDark = theme === 'dark';

    // Create chart
    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: 400,
      layout: {
        background: { color: isDark ? '#161b22' : '#ffffff' },
        textColor: isDark ? '#c9d1d9' : '#202124',
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: isDark ? '#30363d' : '#f1f3f4' },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        autoScale: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
        visible: true,
        // Only show the last price label, hide intermediate labels
        entireTextOnly: true,
      },
      timeScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 20, // Larger right margin space after last candle
        barSpacing: 12, // Spacing to match TradingView's 0.4759 price-to-bar ratio
        minBarSpacing: 0.5,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      localization: {
        // Format timestamps in IST (UTC+5:30)
        timeFormatter: (time) => {
          const date = new Date(time * 1000);
          // Convert to IST by adding 5 hours 30 minutes
          const istOffset = 5.5 * 60 * 60 * 1000;
          const istDate = new Date(date.getTime() + istOffset);
          
          const day = String(istDate.getUTCDate()).padStart(2, '0');
          const month = String(istDate.getUTCMonth() + 1).padStart(2, '0');
          const year = String(istDate.getUTCFullYear()).slice(-2);
          const hours = String(istDate.getUTCHours()).padStart(2, '0');
          const minutes = String(istDate.getUTCMinutes()).padStart(2, '0');
          
          return `${day}/${month}/${year} ${hours}:${minutes}`;
        },
      },
    });

    // Prepare candlestick data
    const candlestickData = candles.map(candle => ({
      time: Math.floor(new Date(candle[CONFIG.COLUMNS.TIMESTAMP]).getTime() / 1000),
      open: parseFloat(candle[CONFIG.COLUMNS.OPEN]),
      high: parseFloat(candle[CONFIG.COLUMNS.HIGH]),
      low: parseFloat(candle[CONFIG.COLUMNS.LOW]),
      close: parseFloat(candle[CONFIG.COLUMNS.CLOSE]),
    })).filter(d => !isNaN(d.time) && !isNaN(d.open));

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#089981',
      downColor: '#f23645',
      borderDownColor: '#f23645',
      borderUpColor: '#089981',
      wickDownColor: '#f23645',
      wickUpColor: '#089981',
      lastValueVisible: true, // Show last price on scale
      priceLineVisible: false, // No horizontal price line
    });
    candlestickSeries.setData(candlestickData);

    // Add Larger Supertrend (sma15) with color based on direction
    this.addSupertrendSeries(chart, candles, 'LARGER', isDark);

    // Add Shorter Supertrend (sma3) with color based on direction
    this.addSupertrendSeries(chart, candles, 'SHORTER', isDark);

    // Add Bands (upperBand and lowerBand) with opacity based on shorter direction
    this.addBandSeries(chart, candles, isDark);

    // Auto-zoom to show last 20 candles with right padding
    if (candlestickData.length > 0) {
      setTimeout(() => {
        const totalCandles = candlestickData.length;
        const showCandles = 20; // Show last 20 candles
        const lastIndex = totalCandles - 1;
        const firstVisibleIndex = Math.max(0, lastIndex - showCandles + 1);
        
        // Set visible logical range to show last 20 candles
        chart.timeScale().setVisibleLogicalRange({
          from: firstVisibleIndex - 0.5,
          to: lastIndex + 5, // More right padding for price scale visibility
        });
      }, 100);
    }

    // Store chart instance
    this.charts.set(containerId, chart);

    // Handle window resize
    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0 || entries[0].target !== container) return;
      const newRect = entries[0].contentRect;
      chart.applyOptions({ 
        width: newRect.width,
        height: 400
      });
    });
    resizeObserver.observe(container);
  }

  /**
   * Add supertrend series (larger or shorter) with dynamic coloring
   * Step line changes values between candles (at candle open), not on the candle itself
   * @param {Object} chart - Chart instance
   * @param {Array} candles - Candle data
   * @param {string} type - 'LARGER' or 'SHORTER'
   * @param {boolean} isDark - Dark theme flag
   */
  addSupertrendSeries(chart, candles, type, isDark) {
    const stColumn = type === 'LARGER' ? CONFIG.COLUMNS.SUPERTREND_LARGER : CONFIG.COLUMNS.SUPERTREND_SHORTER;
    const dirColumn = type === 'LARGER' ? CONFIG.COLUMNS.DIRECTION_LARGER : CONFIG.COLUMNS.DIRECTION_SHORTER;

    // Group data by direction to create colored segments
    let currentDirection = null;
    let currentSegment = [];
    const segments = [];
    let prevValue = null;

    candles.forEach((candle, index) => {
      const time = Math.floor(new Date(candle[CONFIG.COLUMNS.TIMESTAMP]).getTime() / 1000);
      const value = parseFloat(candle[stColumn]);
      const direction = candle[dirColumn];

      if (isNaN(value) || value === null || value === undefined) return;

      if (currentDirection === null || currentDirection !== direction) {
        // Direction changed
        if (currentSegment.length > 0) {
          segments.push({
            data: [...currentSegment],
            direction: currentDirection
          });
          // Start new segment with connection point
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentDirection = direction;
      }

      // Create step effect: horizontal first, then vertical at next candle
      // Add point with previous value (creates horizontal line)
      if (prevValue !== null && prevValue !== value && currentSegment.length > 0) {
        currentSegment.push({ time, value: prevValue });
      }
      
      // Add point with current value (creates vertical step)
      currentSegment.push({ time, value });
      prevValue = value;

      // Last point
      if (index === candles.length - 1 && currentSegment.length > 0) {
        segments.push({
          data: currentSegment,
          direction: currentDirection
        });
      }
    });

    // Render each segment with appropriate color using Simple line type
    segments.forEach(segment => {
      let color;
      
      if (type === 'LARGER') {
        // Larger ST: Green when direction=-1, Red when direction=1
        color = segment.direction === -1 ? '#34a853' : '#f23645';
      } else {
        // Shorter ST: Bright Yellow when direction=-1, Blue when direction=1
        color = segment.direction === -1 ? '#FFD700' : '#1a73e8';
      }

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple, // Use Simple, we create steps manually
        crosshairMarkerVisible: true,
        lastValueVisible: false, // Don't show on price scale
        priceLineVisible: false,
      });

      lineSeries.setData(segment.data);
    });
  }

  /**
   * Add band series (upperBand and lowerBand) with opacity based on shorter direction
   * Step line changes values between candles, not on the candle itself
   * Logic:
   * - When shorter direction = 1: upperBand 100%, lowerBand 50%
   * - When shorter direction = -1: lowerBand 100%, upperBand 50%
   * 
   * @param {Object} chart - Chart instance
   * @param {Array} candles - Candle data
   * @param {boolean} isDark - Dark theme flag
   */
  addBandSeries(chart, candles, isDark) {
    // Create separate segments for upperBand and lowerBand with varying opacity

    // Process upperBand
    let currentOpacity = null;
    let currentSegment = [];
    const upperSegments = [];
    let prevValue = null;

    candles.forEach((candle, index) => {
      const time = Math.floor(new Date(candle[CONFIG.COLUMNS.TIMESTAMP]).getTime() / 1000);
      const value = parseFloat(candle[CONFIG.COLUMNS.UPPERBAND_SHORTER]);
      const direction = candle[CONFIG.COLUMNS.DIRECTION_SHORTER];

      if (isNaN(value) || value === null || value === undefined) return;

      // Opacity: 100% when direction=1, 50% when direction=-1
      const opacity = direction === 1 ? 1.0 : 0.5;

      if (currentOpacity === null || currentOpacity !== opacity) {
        if (currentSegment.length > 0) {
          upperSegments.push({
            data: [...currentSegment],
            opacity: currentOpacity
          });
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentOpacity = opacity;
        prevValue = null; // Reset for new segment
      }

      // Create step effect: horizontal first, then vertical
      if (prevValue !== null && prevValue !== value && currentSegment.length > 0) {
        currentSegment.push({ time, value: prevValue });
      }
      
      currentSegment.push({ time, value });
      prevValue = value;

      if (index === candles.length - 1 && currentSegment.length > 0) {
        upperSegments.push({
          data: currentSegment,
          opacity: currentOpacity
        });
      }
    });

    // Render upperBand segments
    upperSegments.forEach(segment => {
      const alpha = Math.round(segment.opacity * 255).toString(16).padStart(2, '0');
      const color = `#1a73e8${alpha}`; // Blue with varying opacity

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple, // Use Simple, we create steps manually
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });

      lineSeries.setData(segment.data);
    });

    // Process lowerBand
    currentOpacity = null;
    currentSegment = [];
    const lowerSegments = [];
    prevValue = null;

    candles.forEach((candle, index) => {
      const time = Math.floor(new Date(candle[CONFIG.COLUMNS.TIMESTAMP]).getTime() / 1000);
      const value = parseFloat(candle[CONFIG.COLUMNS.LOWERBAND_SHORTER]);
      const direction = candle[CONFIG.COLUMNS.DIRECTION_SHORTER];

      if (isNaN(value) || value === null || value === undefined) return;

      // Opacity: 50% when direction=1, 100% when direction=-1
      const opacity = direction === 1 ? 0.5 : 1.0;

      if (currentOpacity === null || currentOpacity !== opacity) {
        if (currentSegment.length > 0) {
          lowerSegments.push({
            data: [...currentSegment],
            opacity: currentOpacity
          });
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentOpacity = opacity;
        prevValue = null; // Reset for new segment
      }

      // Create step effect: horizontal first, then vertical
      if (prevValue !== null && prevValue !== value && currentSegment.length > 0) {
        currentSegment.push({ time, value: prevValue });
      }
      
      currentSegment.push({ time, value });
      prevValue = value;

      if (index === candles.length - 1 && currentSegment.length > 0) {
        lowerSegments.push({
          data: currentSegment,
          opacity: currentOpacity
        });
      }
    });

    // Render lowerBand segments
    lowerSegments.forEach(segment => {
      const alpha = Math.round(segment.opacity * 255).toString(16).padStart(2, '0');
      const color = `#FFD700${alpha}`; // Bright Yellow with varying opacity

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple, // Use Simple, we create steps manually
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });

      lineSeries.setData(segment.data);
    });
  }

  /**
   * Clear all chart instances
   */
  clearAllCharts() {
    this.charts.forEach(chart => {
      try {
        chart.remove();
      } catch (error) {
        console.warn('Error removing chart:', error);
      }
    });
    this.charts.clear();
  }

  /**
   * Update charts theme when theme changes
   */
  updateChartsTheme() {
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    const isDark = theme === 'dark';

    this.charts.forEach(chart => {
      try {
        chart.applyOptions({
          layout: {
            background: { color: isDark ? '#161b22' : '#ffffff' },
            textColor: isDark ? '#c9d1d9' : '#202124',
          },
          grid: {
            horzLines: { color: isDark ? '#30363d' : '#f1f3f4' },
          },
          rightPriceScale: {
            borderColor: isDark ? '#30363d' : '#dadce0',
          },
          timeScale: {
            borderColor: isDark ? '#30363d' : '#dadce0',
          },
        });
      } catch (error) {
        console.warn('Error updating chart theme:', error);
      }
    });
  }
}

// Create global instance
const chartsManager = new ChartsManager();
console.log('✅ ChartsManager initialized');