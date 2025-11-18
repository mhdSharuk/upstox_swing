/**
 * Chart Renderer Module - FIXED VERSION
 * Handles rendering charts using TradingView Lightweight Charts
 * With proper data validation and timestamp formatting
 */

class ChartRenderer {
  constructor() {
    this.charts = new Map(); // Store chart instances
  }

  /**
   * Format timestamp for TradingView (Unix timestamp in seconds)
   * Assumes input timestamp is in IST
   * @param {string} timestamp - ISO timestamp string (IST)
   * @returns {number} Unix timestamp in seconds
   */
  formatTimestamp(timestamp) {
    try {
      // Parse the date string (assuming it's already in IST)
      const date = new Date(timestamp);
      
      // Check if valid date
      if (isNaN(date.getTime())) {
        console.warn('Invalid timestamp:', timestamp);
        return null;
      }
      
      // Get year, month, day from the date (in UTC to avoid timezone shifts)
      const year = date.getUTCFullYear();
      const month = date.getUTCMonth();
      const day = date.getUTCDate();
      
      // Create new date with 9:15 AM IST
      // IST is UTC+5:30, so 9:15 IST = 3:45 UTC
      const istDate = new Date(Date.UTC(year, month, day, 3, 45, 0, 0));
      
      // Return Unix timestamp in seconds
      return Math.floor(istDate.getTime() / 1000);
    } catch (error) {
      console.error('Error formatting timestamp:', timestamp, error);
      return null;
    }
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
   * @param {number} direction - Current direction (1 or -1)
   */
  renderChart(containerId, symbol, candles, supertrendConfig, direction) {
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

    console.log(`Rendering ${symbol}: ${validCandles.length} valid candles`);

    // Clear existing chart if any
    container.innerHTML = '';

    // Get theme
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    const isDark = theme === 'dark';

    // Create chart
    const chart = LightweightCharts.createChart(container, {
      width: container.clientWidth,
      height: 300,
      layout: {
        background: { color: isDark ? '#161b22' : '#ffffff' },
        textColor: isDark ? '#c9d1d9' : '#202124',
      },
      grid: {
        vertLines: { visible: false }, // Hide vertical grid lines
        horzLines: { visible: false }, // Hide horizontal grid lines
      },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
      },
      timeScale: {
        borderColor: isDark ? '#30363d' : '#dadce0',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 12, // Add right margin (empty space on right)
        barSpacing: 10, // Spacing between bars
        shiftVisibleRangeOnNewBar: true,
      },
      localization: {
        timeFormatter: (time) => {
          // Convert Unix timestamp to IST time string
          const date = new Date(time * 1000);
          // Add 5.5 hours for IST (UTC+5:30)
          const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
          
          // Format as date only for daily data
          const day = istDate.getUTCDate().toString().padStart(2, '0');
          const month = (istDate.getUTCMonth() + 1).toString().padStart(2, '0');
          const year = istDate.getUTCFullYear();
          
          return `${day}/${month}/${year}`;
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
      .filter(d => d !== null) // Remove any invalid entries
      .sort((a, b) => a.time - b.time); // Sort by Unix timestamp (numeric)

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
      .sort((a, b) => a.time - b.time); // Sort by Unix timestamp (numeric)

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
      segments.forEach(segment => {
        const color = segment.direction === 1 ? '#1a73e8' : '#FFD700'; // Blue for long, Yellow for short
        
        const lineSeries = chart.addLineSeries({
          color: color,
          lineWidth: 2,
          lineStyle: 0, // 0 = Solid
          lineType: 1, // 1 = WithSteps (step line: horizontal then vertical)
          crosshairMarkerVisible: true,
          lastValueVisible: false,
          priceLineVisible: false,
          title: '',
        });
        
        lineSeries.setData(segment.data);
      });
    }

    // Set visible range to show last 30 candles
    if (candlestickData.length > 0) {
      const lastIndex = candlestickData.length - 1;
      const firstVisibleIndex = Math.max(0, lastIndex - 29); // Show last 30 candles (0-indexed, so -29)
      
      chart.timeScale().setVisibleLogicalRange({
        from: firstVisibleIndex,
        to: lastIndex + 2, // Add 2 for right margin spacing
      });
    }

    // Store chart instance
    this.charts.set(containerId, chart);

    // Handle window resize
    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0 || entries[0].target !== container) return;
      const newRect = entries[0].contentRect;
      chart.applyOptions({ width: newRect.width });
    });

    resizeObserver.observe(container);

    return chart;
  }

  /**
   * Render multiple charts in a grid
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

    // Clear existing charts
    this.clearAllCharts();
    chartsContainer.innerHTML = '';

    if (symbols.length === 0) {
      chartsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No symbols match the selected filters</div>';
      return;
    }

    // Limit to first 20 symbols to avoid overloading
    const displaySymbols = symbols.slice(0, 20);
    if (symbols.length > 20) {
      console.warn(`Showing first 20 of ${symbols.length} symbols`);
    }

    // Get full data for the timeframe
    const data = await dataLoader.getData(timeframe);

    // Render each symbol's chart
    displaySymbols.forEach((symbolInfo, index) => {
      const { symbol, direction } = symbolInfo;
      
      // Create chart container
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'chart-container';
      chartWrapper.innerHTML = `
        <div class="chart-header">
          <span class="chart-symbol">${symbol}</span>
          <span class="chart-type-badge ${direction === 1 ? 'long' : 'short'}">
            ${direction === 1 ? 'Long' : 'Short'}
          </span>
        </div>
        <div class="chart-canvas" id="chart-${index}"></div>
      `;
      
      chartsContainer.appendChild(chartWrapper);

      // Get all candles for this symbol
      const candles = dataLoader.getSymbolCandles(data, symbol);

      // Render the chart
      setTimeout(() => {
        this.renderChart(`chart-${index}`, symbol, candles, supertrendConfig, direction);
      }, 50 * index); // Stagger chart rendering to avoid blocking UI
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