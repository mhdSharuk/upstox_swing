/**
 * Chart Renderer Module
 * Handles rendering charts using TradingView Lightweight Charts
 */

class ChartRenderer {
  constructor() {
    this.charts = new Map(); // Store chart instances
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
        vertLines: { color: isDark ? '#30363d' : '#f1f3f4' },
        horzLines: { color: isDark ? '#30363d' : '#f1f3f4' },
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
      },
    });

    // Prepare candlestick data
    const candlestickData = candles.map(candle => ({
      time: new Date(candle.timestamp).getTime() / 1000, // Convert to Unix timestamp
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close
    }));

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
    
    const supertrendData = candles
      .filter(candle => candle[supertrendCol] !== null && candle[supertrendCol] !== undefined)
      .map(candle => ({
        time: new Date(candle.timestamp).getTime() / 1000,
        value: candle[supertrendCol],
        direction: candle[directionCol]
      }));

    // Split supertrend data by direction for color coding
    // Yellow for direction -1, Blue for direction 1
    const yellowSegments = [];
    const blueSegments = [];

    supertrendData.forEach((point, index) => {
      if (point.direction === -1) {
        yellowSegments.push({ time: point.time, value: point.value });
        // Add connection point if previous was different
        if (index > 0 && supertrendData[index - 1].direction !== -1) {
          yellowSegments.unshift({ time: supertrendData[index - 1].time, value: supertrendData[index - 1].value });
        }
      } else if (point.direction === 1) {
        blueSegments.push({ time: point.time, value: point.value });
        // Add connection point if previous was different
        if (index > 0 && supertrendData[index - 1].direction !== 1) {
          blueSegments.unshift({ time: supertrendData[index - 1].time, value: supertrendData[index - 1].value });
        }
      }
    });

    // Add supertrend lines
    if (yellowSegments.length > 0) {
      const yellowLine = chart.addLineSeries({
        color: '#FFD700', // Yellow
        lineWidth: 2,
        title: 'Supertrend (Short)',
      });
      yellowLine.setData(yellowSegments);
    }

    if (blueSegments.length > 0) {
      const blueLine = chart.addLineSeries({
        color: '#1a73e8', // Blue
        lineWidth: 2,
        title: 'Supertrend (Long)',
      });
      blueLine.setData(blueSegments);
    }

    // Fit content
    chart.timeScale().fitContent();

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

    // Get full data for the timeframe
    const data = await dataLoader.getData(timeframe);

    // Render each symbol's chart
    symbols.forEach((symbolInfo, index) => {
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
      }, 50); // Small delay to ensure DOM is ready
    });
  }

  /**
   * Clear all chart instances
   */
  clearAllCharts() {
    this.charts.forEach(chart => {
      chart.remove();
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
      chart.applyOptions({
        layout: {
          background: { color: isDark ? '#161b22' : '#ffffff' },
          textColor: isDark ? '#c9d1d9' : '#202124',
        },
        grid: {
          vertLines: { color: isDark ? '#30363d' : '#f1f3f4' },
          horzLines: { color: isDark ? '#30363d' : '#f1f3f4' },
        },
        rightPriceScale: {
          borderColor: isDark ? '#30363d' : '#dadce0',
        },
        timeScale: {
          borderColor: isDark ? '#30363d' : '#dadce0',
        },
      });
    });
  }
}

// Create global instance
const chartRenderer = new ChartRenderer();