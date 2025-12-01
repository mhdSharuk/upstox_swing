/**
 * Charts Manager Module - amCharts Version
 * Same as Lightweight Charts but with STEP LINE supertrends
 * Lazy loading: 20 initial, 10 more on scroll
 */

class ChartsManager {
  constructor() {
    this.charts = new Map(); // Store chart instances
    this.currentStrategy = 'vs';
    this.allSignals = [];
    this.dataBySymbol = null;
    this.loadedCount = 0;
    this.isLoadingMore = false;
    this.INITIAL_BATCH = 20;
    this.LOAD_MORE_BATCH = 10;
  }

  async renderCharts(strategy) {
    this.currentStrategy = strategy;
    console.log('📊 Rendering charts for strategy:', strategy);
    
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-grid').innerHTML = '';
    
    this.clearAllCharts();
    this.loadedCount = 0;
    this.allSignals = [];
    
    try {
      if (!dataLoader.data) {
        await dataLoader.getData();
      }
      
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
      
      this.allSignals = signals;
      this.dataBySymbol = dataLoader.getDataBySymbol();
      
      document.getElementById('charts-loading').style.display = 'none';
      
      this.loadNextBatch(this.INITIAL_BATCH);
      this.setupScrollListener();
      
      console.log(`✓ Initial batch loaded (${Math.min(this.INITIAL_BATCH, signals.length)} charts)`);
      
    } catch (error) {
      console.error('❌ Error rendering charts:', error);
      document.getElementById('charts-loading').style.display = 'none';
      document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">Error loading charts</div>';
    }
  }

  loadNextBatch(count) {
    const chartsGrid = document.getElementById('charts-grid');
    const startIndex = this.loadedCount;
    const endIndex = Math.min(startIndex + count, this.allSignals.length);
    
    console.log(`Loading charts ${startIndex} to ${endIndex - 1}`);
    
    for (let i = startIndex; i < endIndex; i++) {
      const signal = this.allSignals[i];
      const symbol = signal.symbol;
      const candles = this.dataBySymbol.get(symbol);
      
      if (!candles || candles.length === 0) {
        console.warn(`No data for ${symbol}`);
        continue;
      }
      
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
      
      setTimeout(() => {
        this.renderSingleChart(`chart-${i}`, symbol, candles);
      }, 50 * (i - startIndex));
    }
    
    this.loadedCount = endIndex;
    
    if (this.loadedCount >= this.allSignals.length) {
      this.removeLoadingIndicator();
      console.log(`✓ All ${this.loadedCount} charts loaded`);
    } else {
      console.log(`✓ Loaded ${this.loadedCount} / ${this.allSignals.length} charts`);
    }
  }

  setupScrollListener() {
    if (this.scrollListener) {
      window.removeEventListener('scroll', this.scrollListener);
    }
    
    this.scrollListener = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const distanceFromBottom = documentHeight - (scrollTop + windowHeight);
      
      if (distanceFromBottom < 500 && !this.isLoadingMore && this.loadedCount < this.allSignals.length) {
        this.loadMore();
      }
    };
    
    window.addEventListener('scroll', this.scrollListener);
  }

  async loadMore() {
    if (this.isLoadingMore || this.loadedCount >= this.allSignals.length) {
      return;
    }
    
    this.isLoadingMore = true;
    console.log('📥 Loading more charts...');
    this.showLoadingIndicator();
    
    await new Promise(resolve => setTimeout(resolve, 100));
    this.loadNextBatch(this.LOAD_MORE_BATCH);
    this.isLoadingMore = false;
  }

  showLoadingIndicator() {
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

  removeLoadingIndicator() {
    const indicator = document.getElementById('charts-load-more');
    if (indicator) indicator.remove();
  }

  renderSingleChart(containerId, symbol, candles) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container ${containerId} not found`);
      return;
    }

    // Get theme
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    const isDark = theme === 'dark';

    // Create root
    const root = am5.Root.new(container);

    // Set theme
    if (isDark) {
      root.setThemes([am5themes_Dark.new(root)]);
    } else {
      root.setThemes([am5themes_Animated.new(root)]);
    }

    // Create chart
    const chart = root.container.children.push(
      am5xy.XYChart.new(root, {
        panX: true,
        panY: true,
        wheelX: "panX",
        wheelY: "zoomX",
        pinchZoomX: true,
        paddingLeft: 0,
        paddingRight: 20
      })
    );

    // Create axes
    const xAxis = chart.xAxes.push(
      am5xy.DateAxis.new(root, {
        baseInterval: { timeUnit: "minute", count: 125 },
        renderer: am5xy.AxisRendererX.new(root, {}),
        tooltip: am5.Tooltip.new(root, {})
      })
    );

    const yAxis = chart.yAxes.push(
      am5xy.ValueAxis.new(root, {
        renderer: am5xy.AxisRendererY.new(root, {})
      })
    );

    // Prepare candlestick data
    const chartData = candles.map(candle => ({
      date: new Date(candle[CONFIG.COLUMNS.TIMESTAMP]).getTime(),
      open: parseFloat(candle[CONFIG.COLUMNS.OPEN]),
      high: parseFloat(candle[CONFIG.COLUMNS.HIGH]),
      low: parseFloat(candle[CONFIG.COLUMNS.LOW]),
      close: parseFloat(candle[CONFIG.COLUMNS.CLOSE]),
      st_larger: parseFloat(candle[CONFIG.COLUMNS.SUPERTREND_LARGER]),
      st_shorter: parseFloat(candle[CONFIG.COLUMNS.SUPERTREND_SHORTER]),
      dir_larger: candle[CONFIG.COLUMNS.DIRECTION_LARGER],
      dir_shorter: candle[CONFIG.COLUMNS.DIRECTION_SHORTER],
      upper_band: parseFloat(candle[CONFIG.COLUMNS.UPPERBAND_SHORTER]),
      lower_band: parseFloat(candle[CONFIG.COLUMNS.LOWERBAND_SHORTER])
    }));

    // Add candlestick series
    const candlestickSeries = chart.series.push(
      am5xy.CandlestickSeries.new(root, {
        name: symbol,
        xAxis: xAxis,
        yAxis: yAxis,
        valueYField: "close",
        openValueYField: "open",
        lowValueYField: "low",
        highValueYField: "high",
        valueXField: "date",
        tooltip: am5.Tooltip.new(root, {
          labelText: "O: {openValueY}\nH: {highValueY}\nL: {lowValueY}\nC: {valueY}"
        })
      })
    );

    candlestickSeries.data.setAll(chartData);

    // Add supertrends as STEP LINES
    this.addSupertrendStepLine(root, chart, xAxis, yAxis, chartData, 'LARGER');
    this.addSupertrendStepLine(root, chart, xAxis, yAxis, chartData, 'SHORTER');

    // Add bands
    this.addBandLines(root, chart, xAxis, yAxis, chartData);

    // Add cursor
    chart.set("cursor", am5xy.XYCursor.new(root, {
      behavior: "zoomX"
    }));

    // Zoom to last 20 candles
    const dataLength = chartData.length;
    if (dataLength > 20) {
      const startIndex = dataLength - 20;
      xAxis.zoomToIndexes(startIndex, dataLength - 1);
    }

    // Store chart instance
    this.charts.set(containerId, { root, chart });
  }

  addSupertrendStepLine(root, chart, xAxis, yAxis, data, type) {
    const valueField = type === 'LARGER' ? 'st_larger' : 'st_shorter';
    const dirField = type === 'LARGER' ? 'dir_larger' : 'dir_shorter';

    // Group by direction
    let segments = [];
    let currentSegment = [];
    let currentDir = null;

    data.forEach((point, index) => {
      if (isNaN(point[valueField])) return;

      if (currentDir === null || currentDir !== point[dirField]) {
        if (currentSegment.length > 0) {
          segments.push({ data: currentSegment, direction: currentDir });
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentDir = point[dirField];
      }

      currentSegment.push({
        date: point.date,
        value: point[valueField]
      });

      if (index === data.length - 1 && currentSegment.length > 0) {
        segments.push({ data: currentSegment, direction: currentDir });
      }
    });

    // Render segments with step lines
    segments.forEach(segment => {
      let color;
      if (type === 'LARGER') {
        color = segment.direction === -1 ? am5.color(0x34a853) : am5.color(0xf23645);
      } else {
        color = segment.direction === -1 ? am5.color(0xFFD700) : am5.color(0x1a73e8);
      }

      const series = chart.series.push(
        am5xy.StepLineSeries.new(root, {
          name: `${type}_ST`,
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: "value",
          valueXField: "date",
          stroke: color,
          strokeWidth: 2,
          noRisers: false, // Show vertical steps
          connect: false
        })
      );

      series.data.setAll(segment.data);
      series.strokes.template.setAll({
        strokeWidth: 2
      });
    });
  }

  addBandLines(root, chart, xAxis, yAxis, data) {
    // Upper band segments
    let upperSegments = [];
    let currentSegment = [];
    let currentOpacity = null;

    data.forEach((point, index) => {
      if (isNaN(point.upper_band)) return;

      const opacity = point.dir_shorter === 1 ? 1.0 : 0.5;

      if (currentOpacity === null || currentOpacity !== opacity) {
        if (currentSegment.length > 0) {
          upperSegments.push({ data: currentSegment, opacity: currentOpacity });
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentOpacity = opacity;
      }

      currentSegment.push({
        date: point.date,
        value: point.upper_band
      });

      if (index === data.length - 1 && currentSegment.length > 0) {
        upperSegments.push({ data: currentSegment, opacity: currentOpacity });
      }
    });

    upperSegments.forEach(segment => {
      const series = chart.series.push(
        am5xy.StepLineSeries.new(root, {
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: "value",
          valueXField: "date",
          stroke: am5.color(0x1a73e8),
          strokeWidth: 1,
          strokeOpacity: segment.opacity,
          noRisers: false
        })
      );
      series.data.setAll(segment.data);
    });

    // Lower band segments
    let lowerSegments = [];
    currentSegment = [];
    currentOpacity = null;

    data.forEach((point, index) => {
      if (isNaN(point.lower_band)) return;

      const opacity = point.dir_shorter === 1 ? 0.5 : 1.0;

      if (currentOpacity === null || currentOpacity !== opacity) {
        if (currentSegment.length > 0) {
          lowerSegments.push({ data: currentSegment, opacity: currentOpacity });
          currentSegment = [currentSegment[currentSegment.length - 1]];
        }
        currentOpacity = opacity;
      }

      currentSegment.push({
        date: point.date,
        value: point.lower_band
      });

      if (index === data.length - 1 && currentSegment.length > 0) {
        lowerSegments.push({ data: currentSegment, opacity: currentOpacity });
      }
    });

    lowerSegments.forEach(segment => {
      const series = chart.series.push(
        am5xy.StepLineSeries.new(root, {
          xAxis: xAxis,
          yAxis: yAxis,
          valueYField: "value",
          valueXField: "date",
          stroke: am5.color(0xFFD700),
          strokeWidth: 1,
          strokeOpacity: segment.opacity,
          noRisers: false
        })
      );
      series.data.setAll(segment.data);
    });
  }

  clearAllCharts() {
    this.charts.forEach(({ root }) => {
      try {
        root.dispose();
      } catch (error) {
        console.warn('Error disposing chart:', error);
      }
    });
    this.charts.clear();
    
    if (this.scrollListener) {
      window.removeEventListener('scroll', this.scrollListener);
      this.scrollListener = null;
    }
  }

  updateChartsTheme() {
    // Theme changes require recreation in amCharts
    console.log('Theme changed - refresh page to see updated charts');
  }
}

// Create global instance
const chartsManager = new ChartsManager();
console.log('✅ ChartsManager initialized (amCharts with step lines)');