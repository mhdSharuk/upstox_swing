/**
 * Chart Renderer Module - UPDATED VERSION
 * Handles rendering charts using TradingView Lightweight Charts
 * With proper data validation and timestamp formatting
 * UPDATED: Different date formats for daily vs 125min
 * ADDED: Lazy loading with Intersection Observer API for infinite scroll
 */

class ChartRenderer {
  constructor() {
    this.charts = new Map(); // Store chart instances
    this.observer = null; // Intersection Observer instance
    this.chartBatchSize = 20; // Number of charts to load at once
    this.currentBatchIndex = 0; // Track current batch
    this.allSymbols = []; // Store all symbols to render
    this.currentSupertrendConfig = ''; // Store current supertrend config
    this.currentTimeframe = ''; // Store current timeframe
    this.isLoadingBatch = false; // Prevent multiple simultaneous loads
  }

  /**
   * Format timestamp for TradingView (Unix timestamp in seconds)
   * @param {string} timestamp - ISO timestamp string
   * @returns {number} Unix timestamp in seconds
   */
  formatTimestamp(timestamp) {
    try {
      const date = new Date(timestamp);
      
      // Check if valid date
      if (isNaN(date.getTime())) {
        console.warn('Invalid timestamp:', timestamp);
        return null;
      }
      
      // Return Unix timestamp in seconds (no timezone manipulation needed)
      return Math.floor(date.getTime() / 1000);
    } catch (error) {
      console.error('Error formatting timestamp:', timestamp, error);
      return null;
    }
  }

  /**
   * Format date for display based on timeframe
   * @param {number} time - Unix timestamp in seconds
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {string} Formatted date string
   */
  formatDateForDisplay(time, timeframe) {
    const date = new Date(time * 1000);
    
    // Day names (3 letters)
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const day = dayNames[date.getDay()];
    
    // Month names (3 letters)
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = monthNames[date.getMonth()];
    
    // Date and year
    const dateNum = date.getDate();
    const year = String(date.getFullYear()).slice(-2); // Last 2 digits
    
    // For daily: "Thu 19 Nov '25"
    if (timeframe === 'daily') {
      return `${day} ${dateNum} ${month} '${year}`;
    }
    
    // For 125min: "Thu 19 Nov '25 13:25"
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day} ${dateNum} ${month} '${year} ${hours}:${minutes}`;
  }

  /**
   * Validate candle data
   * @param {Object} candle - Single candle object
   * @returns {boolean} True if valid
   */
  isValidCandle(candle) {
    return candle &&
           candle.open != null && !isNaN(candle.open) &&
           candle.high != null && !isNaN(candle.high) &&
           candle.low != null && !isNaN(candle.low) &&
           candle.close != null && !isNaN(candle.close) &&
           candle.timestamp != null;
  }

  /**
   * Create and render a chart for a symbol
   * @param {string} containerId - DOM element ID for the chart
   * @param {string} symbol - Trading symbol
   * @param {Array} candles - Array of candle data for the symbol
   * @param {string} supertrendConfig - Supertrend configuration ID
   * @param {number} direction - Current direction (-1 or 1)
   * @param {string} timeframe - 'daily' or 'min125' for date formatting
   */
  renderChart(containerId, symbol, candles, supertrendConfig, direction, timeframe = 'daily') {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Validate candles
    if (!candles || candles.length === 0) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No data available</div>';
      return;
    }

    // Filter valid candles
    const validCandles = candles.filter(c => this.isValidCandle(c));
    
    if (validCandles.length === 0) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No valid data</div>';
      console.warn(`No valid candles for ${symbol}`);
      return;
    }

    console.log(`Rendering ${symbol} (${timeframe}): ${validCandles.length} valid candles`);

    // Clear existing chart if any
    container.innerHTML = '';

    // Get theme
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    const isDark = theme === 'dark';

    // Get container dimensions
    const containerHeight = container.clientHeight || 300;
    const containerWidth = container.clientWidth;

    // Create chart with proper sizing and date formatting
    const chart = LightweightCharts.createChart(container, {
      width: containerWidth,
      height: containerHeight,
      layout: {
        background: { color: isDark ? '#161b22' : '#ffffff' },
        textColor: isDark ? '#c9d1d9' : '#202124',
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        autoScale: true,
        scaleMargins: {
          top: 0.1,    // 10% margin at top
          bottom: 0.1, // 10% margin at bottom
        },
      },
      timeScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 10,       // Right margin for breathing room
        barSpacing: 8,         // Comfortable spacing between bars
        minBarSpacing: 0.5,    // Minimum spacing when zoomed out
        fixLeftEdge: false,
        fixRightEdge: false,
        shiftVisibleRangeOnNewBar: true,
      },
      localization: {
        timeFormatter: (time) => {
          // Use different formats based on timeframe
          return this.formatDateForDisplay(time, timeframe);
        },
      },
    });

    // Prepare candlestick data
    const candlestickData = validCandles
      .map(candle => {
        const time = this.formatTimestamp(candle.timestamp);
        if (!time) return null;
        
        return {
          time: time,
          open: parseFloat(candle.open),
          high: parseFloat(candle.high),
          low: parseFloat(candle.low),
          close: parseFloat(candle.close)
        };
      })
      .filter(d => d !== null)
      .sort((a, b) => a.time - b.time);

    if (candlestickData.length === 0) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No valid timestamp data</div>';
      return;
    }

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#0f9d58',
      downColor: '#d93025',
      borderDownColor: '#d93025',
      borderUpColor: '#0f9d58',
      wickDownColor: '#d93025',
      wickUpColor: '#0f9d58',
    });

    candlestickSeries.setData(candlestickData);

    // Prepare supertrend line data
    const supertrendCol = `supertrend_${supertrendConfig}`;
    const directionCol = `direction_${supertrendConfig}`;
    
    const supertrendData = validCandles
      .filter(candle => {
        const stValue = candle[supertrendCol];
        return stValue != null && !isNaN(stValue);
      })
      .map(candle => {
        const time = this.formatTimestamp(candle.timestamp);
        if (!time) return null;
        
        return {
          time: time,
          value: parseFloat(candle[supertrendCol]),
          direction: candle[directionCol]
        };
      })
      .filter(d => d !== null)
      .sort((a, b) => a.time - b.time);

    if (supertrendData.length > 0) {
      // Create continuous segments that change color based on direction
      let currentDirection = null;
      let currentSegment = [];
      const segments = [];

      supertrendData.forEach((point, index) => {
        if (currentDirection === null || currentDirection !== point.direction) {
          // Direction changed or first point
          if (currentSegment.length > 0) {
            // Save the previous segment
            segments.push({
              data: [...currentSegment],
              direction: currentDirection
            });
            // Start new segment with connection point (last point of previous segment)
            currentSegment = [currentSegment[currentSegment.length - 1]];
          }
          currentDirection = point.direction;
        }
        
        currentSegment.push({ time: point.time, value: point.value });
        
        // If last point, save the segment
        if (index === supertrendData.length - 1 && currentSegment.length > 0) {
          segments.push({
            data: currentSegment,
            direction: currentDirection
          });
        }
      });

      // Render each segment as step line
      // Blue when direction = 1, Yellow when direction = -1
      segments.forEach(segment => {
        const color = segment.direction === 1 ? '#1a73e8' : '#FFD700';
        
        const lineSeries = chart.addLineSeries({
          color: color,
          lineWidth: 2,
          lineStyle: 0,
          lineType: 1,
          crosshairMarkerVisible: true,
          lastValueVisible: false,
          priceLineVisible: false,
          title: '',
        });
        
        lineSeries.setData(segment.data);
      });
    }

    // Auto-zoom to show last 3 months of candles with proper spacing and right margin
    if (candlestickData.length > 0) {
      const totalCandles = candlestickData.length;
      
      // Calculate 3 months worth of candles based on timeframe
      // Daily: ~63 trading days (21 trading days/month × 3 months)
      // 125min: ~48 candles (3 candles/day × 5 days/week × 3.2 weeks/month × 3 months)
      const showCandles = Math.min(63, totalCandles); // Show last 3 months or all if less
      
      const lastIndex = totalCandles - 1;
      const firstVisibleIndex = Math.max(0, lastIndex - showCandles + 1);
      
      // Use logical range for precise control (indices, not time values)
      setTimeout(() => {
        chart.timeScale().setVisibleLogicalRange({
          from: firstVisibleIndex - 0.5, // Small left padding
          to: lastIndex + 7, // Right margin: 7 candles worth of space
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
        height: newRect.height || 300
      });
    });

    resizeObserver.observe(container);

    return chart;
  }

  /**
   * Render multiple charts in a grid with lazy loading
   * @param {Array} symbols - Array of symbol objects with candle data
   * @param {string} supertrendConfig - Supertrend configuration ID
   * @param {string} timeframe - 'daily' or 'min125'
   */
  async renderChartsGrid(symbols, supertrendConfig, timeframe) {
    const chartsContainer = document.getElementById('charts-grid');
    if (!chartsContainer) {
      console.error('Charts grid container not found');
      return;
    }

    // Clear existing charts and observer
    this.clearAllCharts();
    this.disconnectObserver();
    chartsContainer.innerHTML = '';

    if (symbols.length === 0) {
      chartsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No symbols match the selected filters</div>';
      return;
    }

    // Store all symbols and config for lazy loading
    this.allSymbols = symbols;
    this.currentSupertrendConfig = supertrendConfig;
    this.currentTimeframe = timeframe;
    this.currentBatchIndex = 0;
    this.isLoadingBatch = false;

    console.log(`📊 Total symbols to render: ${symbols.length}`);
    console.log(`📊 Using lazy loading with batch size: ${this.chartBatchSize}`);

    // Load first batch
    await this.loadNextBatch();

    // Setup lazy loading if there are more charts to load
    if (symbols.length > this.chartBatchSize) {
      this.setupLazyLoading();
    }
  }

  /**
   * Load next batch of charts
   */
  async loadNextBatch() {
    if (this.isLoadingBatch) {
      console.log('⏳ Already loading a batch, skipping...');
      return;
    }

    const startIndex = this.currentBatchIndex * this.chartBatchSize;
    const endIndex = Math.min(startIndex + this.chartBatchSize, this.allSymbols.length);

    if (startIndex >= this.allSymbols.length) {
      console.log('✓ All charts loaded');
      this.removeSentinel();
      return;
    }

    this.isLoadingBatch = true;
    console.log(`📊 Loading batch ${this.currentBatchIndex + 1}: symbols ${startIndex + 1} to ${endIndex}`);

    const chartsContainer = document.getElementById('charts-grid');
    const batchSymbols = this.allSymbols.slice(startIndex, endIndex);

    // Get full data for the timeframe
    const data = await dataLoader.getData(this.currentTimeframe);

    // Render each symbol's chart in this batch
    for (let i = 0; i < batchSymbols.length; i++) {
      const symbolInfo = batchSymbols[i];
      const { symbol, direction } = symbolInfo;
      const chartIndex = startIndex + i;

      // Create chart container
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'chart-container';
      chartWrapper.innerHTML = `
        <div class="chart-header">
          <span class="chart-symbol">${symbol}</span>
          <span class="chart-type-badge ${direction === -1 ? 'long' : 'short'}">
            ${direction === -1 ? 'Long' : 'Short'}
          </span>
        </div>
        <div class="chart-canvas" id="chart-${chartIndex}"></div>
      `;

      // Insert before sentinel (or append if no sentinel)
      const sentinel = document.getElementById('charts-sentinel');
      if (sentinel) {
        chartsContainer.insertBefore(chartWrapper, sentinel);
      } else {
        chartsContainer.appendChild(chartWrapper);
      }

      // Get all candles for this symbol
      const candles = dataLoader.getSymbolCandles(data, symbol);

      // Render the chart (stagger to prevent blocking UI)
      setTimeout(() => {
        this.renderChart(`chart-${chartIndex}`, symbol, candles, this.currentSupertrendConfig, direction, this.currentTimeframe);
      }, 50 * i);
    }

    this.currentBatchIndex++;
    this.isLoadingBatch = false;

    // Check if there are more charts to load
    if (endIndex < this.allSymbols.length) {
      // Ensure sentinel exists
      if (!document.getElementById('charts-sentinel')) {
        this.createSentinel();
      }
    } else {
      // All charts loaded, remove sentinel
      this.removeSentinel();
    }
  }

  /**
   * Setup Intersection Observer for lazy loading
   */
  setupLazyLoading() {
    console.log('🔍 Setting up Intersection Observer for lazy loading...');

    // Create sentinel element
    this.createSentinel();

    // Create Intersection Observer
    const options = {
      root: null, // viewport
      rootMargin: '200px', // Start loading 200px before sentinel is visible
      threshold: 0.01 // Trigger when even 1% is visible
    };

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !this.isLoadingBatch) {
          console.log('📍 Sentinel visible, loading next batch...');
          this.loadNextBatch();
        }
      });
    }, options);

    // Observe the sentinel
    const sentinel = document.getElementById('charts-sentinel');
    if (sentinel) {
      this.observer.observe(sentinel);
      console.log('✓ Observer watching sentinel');
    }
  }

  /**
   * Create sentinel element for lazy loading
   */
  createSentinel() {
    const chartsContainer = document.getElementById('charts-grid');
    if (!chartsContainer) return;

    // Remove existing sentinel if any
    this.removeSentinel();

    // Create new sentinel
    const sentinel = document.createElement('div');
    sentinel.id = 'charts-sentinel';
    sentinel.className = 'charts-loading-sentinel';
    sentinel.innerHTML = `
      <div class="spinner"></div>
      <div>Loading more charts...</div>
    `;

    chartsContainer.appendChild(sentinel);
  }

  /**
   * Remove sentinel element
   */
  removeSentinel() {
    const sentinel = document.getElementById('charts-sentinel');
    if (sentinel) {
      sentinel.remove();
      console.log('✓ Sentinel removed');
    }
  }

  /**
   * Disconnect Intersection Observer
   */
  disconnectObserver() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
      console.log('✓ Observer disconnected');
    }
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
   * Update chart theme when theme changes
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
            vertLines: { visible: false },
            horzLines: { visible: false },
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
const chartRenderer = new ChartRenderer();