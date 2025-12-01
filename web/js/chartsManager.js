/**
 * Charts Manager Module - WITH LAZY LOADING
 * Renders OHLC candles with larger/shorter supertrends and bands
 * Uses TradingView Lightweight Charts library
 * 
 * LAZY LOADING: Loads 20 charts initially, then 10 more on scroll
 */

class ChartsManager {
  constructor() {
    this.charts = new Map(); // Store chart instances
    this.currentStrategy = 'vs'; // Default strategy
    this.allSignals = []; // Store all signals for lazy loading
    this.dataBySymbol = null; // Cache data by symbol
    this.loadedCount = 0; // Track how many charts are loaded
    this.isLoadingMore = false; // Prevent multiple simultaneous loads
    this.INITIAL_BATCH = 20; // Load first 20 charts
    this.LOAD_MORE_BATCH = 10; // Load 10 more on scroll
  }

  /**
   * Render charts for selected strategy with lazy loading
   * @param {string} strategy - 'vs' or 'vb'
   */
  async renderCharts(strategy) {
    this.currentStrategy = strategy;
    
    console.log('📊 Rendering charts for strategy:', strategy);
    
    // Show loading
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-grid').innerHTML = '';
    
    // Clear existing charts and state
    this.clearAllCharts();
    this.loadedCount = 0;
    this.allSignals = [];
    
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
      
      // Store signals and data for lazy loading
      this.allSignals = signals;
      this.dataBySymbol = dataLoader.getDataBySymbol();
      
      // Hide initial loading
      document.getElementById('charts-loading').style.display = 'none';
      
      // Load first batch (20 charts)
      this.loadNextBatch(this.INITIAL_BATCH);
      
      // Setup scroll listener for infinite scroll
      this.setupScrollListener();
      
      console.log(`✓ Initial batch loaded (${Math.min(this.INITIAL_BATCH, signals.length)} charts)`);
      
    } catch (error) {
      console.error('❌ Error rendering charts:', error);
      document.getElementById('charts-loading').style.display = 'none';
      document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">Error loading charts</div>';
    }
  }

  /**
   * Load next batch of charts
   * @param {number} count - Number of charts to load
   */
  loadNextBatch(count) {
    const chartsGrid = document.getElementById('charts-grid');
    
    // Calculate range
    const startIndex = this.loadedCount;
    const endIndex = Math.min(startIndex + count, this.allSignals.length);
    
    console.log(`Loading charts ${startIndex} to ${endIndex - 1}`);
    
    // Load charts in batch
    for (let i = startIndex; i < endIndex; i++) {
      const signal = this.allSignals[i];
      const symbol = signal.symbol;
      const candles = this.dataBySymbol.get(symbol);
      
      if (!candles || candles.length === 0) {
        console.warn(`No data for ${symbol}`);
        continue;
      }
      
      // Create chart container
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'chart-container';
      chartWrapper.innerHTML = `
        <div class="chart-header">
          <span class="chart-symbol">${symbol}</span>
          <span class="chart-info">₹${signal.close}</span>
        </div>
        <div class="chart-canvas" id="chart-${i}"></div>
      `;
      
      chartsGrid.appendChild(chartWrapper);
      
      // Render the chart with slight delay to prevent UI freeze
      setTimeout(() => {
        this.renderSingleChart(`chart-${i}`, symbol, candles);
      }, 50 * (i - startIndex));
    }
    
    // Update loaded count
    this.loadedCount = endIndex;
    
    // Remove loading indicator if all charts are loaded
    if (this.loadedCount >= this.allSignals.length) {
      this.removeLoadingIndicator();
      console.log(`✓ All ${this.loadedCount} charts loaded`);
    } else {
      console.log(`✓ Loaded ${this.loadedCount} / ${this.allSignals.length} charts`);
    }
  }

  /**
   * Setup scroll listener for infinite scroll
   */
  setupScrollListener() {
    // Remove existing listener if any
    if (this.scrollListener) {
      window.removeEventListener('scroll', this.scrollListener);
    }
    
    // Create scroll listener
    this.scrollListener = () => {
      // Check if user scrolled near bottom (within 500px)
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      
      const distanceFromBottom = documentHeight - (scrollTop + windowHeight);
      
      // Load more if:
      // 1. Within 500px of bottom
      // 2. Not currently loading
      // 3. More charts available
      if (distanceFromBottom < 500 && !this.isLoadingMore && this.loadedCount < this.allSignals.length) {
        this.loadMore();
      }
    };
    
    // Attach listener
    window.addEventListener('scroll', this.scrollListener);
  }

  /**
   * Load more charts when scrolling
   */
  async loadMore() {
    if (this.isLoadingMore || this.loadedCount >= this.allSignals.length) {
      return;
    }
    
    this.isLoadingMore = true;
    console.log('📥 Loading more charts...');
    
    // Show loading indicator
    this.showLoadingIndicator();
    
    // Small delay for smooth UX
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Load next batch (10 charts)
    this.loadNextBatch(this.LOAD_MORE_BATCH);
    
    this.isLoadingMore = false;
  }

  /**
   * Show loading indicator at bottom of grid
   */
  showLoadingIndicator() {
    // Remove existing indicator
    this.removeLoadingIndicator();
    
    const chartsGrid = document.getElementById('charts-grid');
    const indicator = document.createElement('div');
    indicator.id = 'charts-load-more';
    indicator.style.cssText = 'grid-column: 1/-1; text-align: center; padding: 20px; color: var(--text-secondary);';
    indicator.innerHTML = `
      <div style="display: inline-block;">
        <div style="border: 3px solid var(--spinner-border); border-top: 3px solid var(--accent-blue); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px;"></div>
        <div>Loading more charts...</div>
      </div>
    `;
    
    chartsGrid.appendChild(indicator);
  }

  /**
   * Remove loading indicator
   */
  removeLoadingIndicator() {
    const indicator = document.getElementById('charts-load-more');
    if (indicator) {
      indicator.remove();
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
        entireTextOnly: true,
      },
      timeScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 20,
        barSpacing: 12,
        minBarSpacing: 0.5,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      localization: {
        timeFormatter: (time) => {
          const date = new Date(time * 1000);
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
      lastValueVisible: true,
      priceLineVisible: false,
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
        const showCandles = 20;
        const lastIndex = totalCandles - 1;
        const firstVisibleIndex = Math.max(0, lastIndex - showCandles + 1);
        
        chart.timeScale().setVisibleLogicalRange({
          from: firstVisibleIndex - 0.5,
          to: lastIndex + 5,
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
      if (prevValue !== null && prevValue !== value && currentSegment.length > 0) {
        currentSegment.push({ time, value: prevValue });
      }
      
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

    // Render each segment with appropriate color
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
        lineType: LightweightCharts.LineType.Simple,
        crosshairMarkerVisible: true,
        lastValueVisible: false,
        priceLineVisible: false,
      });

      lineSeries.setData(segment.data);
    });
  }

  /**
   * Add band series (upperBand and lowerBand) with opacity based on shorter direction
   * @param {Object} chart - Chart instance
   * @param {Array} candles - Candle data
   * @param {boolean} isDark - Dark theme flag
   */
  addBandSeries(chart, candles, isDark) {
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
        prevValue = null;
      }

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
      const color = `#1a73e8${alpha}`;

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple,
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
        prevValue = null;
      }

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
      const color = `#FFD700${alpha}`;

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 1,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple,
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
    
    // Remove scroll listener
    if (this.scrollListener) {
      window.removeEventListener('scroll', this.scrollListener);
      this.scrollListener = null;
    }
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
console.log('✅ ChartsManager initialized with lazy loading (20 initial, 10 per scroll)');