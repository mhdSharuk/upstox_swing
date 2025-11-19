/**
 * Chart Renderer Module - FIXED VERSION
 * Handles rendering charts using TradingView Lightweight Charts
 * With proper data validation and timestamp formatting
 * FIX: Blue for direction 1, Yellow for direction -1
 */

class ChartRenderer {
  constructor() {
    this.charts = new Map(); // Store chart instances
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

    // Get container dimensions
    const containerHeight = container.clientHeight || 300;
    const containerWidth = container.clientWidth;

    // Create chart with proper sizing
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
          // Convert Unix timestamp to date string
          const date = new Date(time * 1000);
          
          // Format as DD/MM/YYYY
          const day = date.getDate().toString().padStart(2, '0');
          const month = (date.getMonth() + 1).toString().padStart(2, '0');
          const year = date.getFullYear();
          
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
      // direction -1 = Long, direction 1 = Short (for badge display)
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'chart-container';
      chartWrapper.innerHTML = `
        <div class="chart-header">
          <span class="chart-symbol">${symbol}</span>
          <span class="chart-type-badge ${direction === -1 ? 'long' : 'short'}">
            ${direction === -1 ? 'Long' : 'Short'}
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