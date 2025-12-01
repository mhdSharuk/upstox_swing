class ChartsManager {
  constructor() {
    this.charts = new Map();
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
    document.getElementById('charts-loading').style.display = 'block';
    document.getElementById('charts-grid').innerHTML = '';
    this.clearAllCharts();
    this.loadedCount = 0;
    this.allSignals = [];
    try {
      if (!dataLoader.data) await dataLoader.getData();
      let signals = strategy === 'vs'
        ? filtersManager.detectVolatilitySupport(parseFloat(document.getElementById('pctdiff-filter').value) || 2.5)
        : filtersManager.detectVolatilityBreakout();
      if (!signals || signals.length === 0) {
        document.getElementById('charts-loading').style.display = 'none';
        document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);">No symbols found</div>';
        return;
      }
      this.allSignals = signals;
      this.dataBySymbol = dataLoader.getDataBySymbol();
      document.getElementById('charts-loading').style.display = 'none';
      this.loadNextBatch(this.INITIAL_BATCH);
      this.setupScrollListener();
    } catch (error) {
      document.getElementById('charts-loading').style.display = 'none';
      document.getElementById('charts-grid').innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px;">Error loading charts</div>';
      console.error(error);
    }
  }

  loadNextBatch(count) {
    const grid = document.getElementById('charts-grid');
    const start = this.loadedCount;
    const end = Math.min(start + count, this.allSignals.length);
    for (let i = start; i < end; i++) {
      const signal = this.allSignals[i];
      const symbol = signal.symbol;
      const candles = this.dataBySymbol.get(symbol);
      if (!candles || candles.length === 0) continue;
      const wrap = document.createElement('div');
      wrap.className = 'chart-container';
      wrap.innerHTML = `
        <div class="chart-header">
          <span class="chart-symbol">${symbol}</span>
          <span class="chart-info">₹${signal.close}</span>
        </div>
        <div class="chart-canvas" id="chart-${i}"></div>
      `;
      grid.appendChild(wrap);
      setTimeout(() => this.renderSingleChart(`chart-${i}`, symbol, candles), 50 * (i - start));
    }
    this.loadedCount = end;
    if (this.loadedCount >= this.allSignals.length) this.removeLoadingIndicator();
  }

  setupScrollListener() {
    if (this.scrollListener) window.removeEventListener('scroll', this.scrollListener);
    this.scrollListener = () => {
      const st = window.pageYOffset || document.documentElement.scrollTop;
      const wh = window.innerHeight;
      const dh = document.documentElement.scrollHeight;
      if (dh - (st + wh) < 500 && !this.isLoadingMore && this.loadedCount < this.allSignals.length) this.loadMore();
    };
    window.addEventListener('scroll', this.scrollListener);
  }

  async loadMore() {
    if (this.isLoadingMore || this.loadedCount >= this.allSignals.length) return;
    this.isLoadingMore = true;
    this.showLoadingIndicator();
    await new Promise(r => setTimeout(r, 100));
    this.loadNextBatch(this.LOAD_MORE_BATCH);
    this.isLoadingMore = false;
  }

  showLoadingIndicator() {
    this.removeLoadingIndicator();
    const g = document.getElementById('charts-grid');
    const el = document.createElement('div');
    el.id = 'charts-load-more';
    el.style.cssText = 'grid-column: 1/-1; text-align: center; padding: 20px;';
    el.innerHTML = `
      <div style="display: inline-block;">
        <div style="border: 3px solid #ccc; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px;"></div>
        <div>Loading…</div>
      </div>`;
    g.appendChild(el);
  }

  removeLoadingIndicator() {
    const el = document.getElementById('charts-load-more');
    if (el) el.remove();
  }



  sanitizeAndSortPoints(points) {
    const map = Object.create(null);
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      if (!p) continue;
      const t = Number(p.time);
      const v = Number(p.value);
      if (!Number.isFinite(t) || !Number.isFinite(v)) continue;
      map[t] = { time: t, value: v };
    }
    const keys = Object.keys(map).map(k => Number(k)).sort((a, b) => a - b);
    return keys.map(k => map[k]);
  }

  renderSingleChart(containerId, symbol, candles) {
    const c = document.getElementById(containerId);
    if (!c) return;

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const labelMap = Object.create(null);
    const ohlcIndexed = [];

    for (let i = 0; i < candles.length; i++) {
      const row = candles[i];
      const tsRaw = new Date(row[CONFIG.COLUMNS.TIMESTAMP]).getTime();
      if (!Number.isFinite(tsRaw)) continue;
      const istMs = tsRaw + 19800000;
      const timeLabel = (() => {
        const d = new Date(istMs);
        const day = String(d.getUTCDate()).padStart(2, '0');
        const month = String(d.getUTCMonth() + 1).padStart(2, '0');
        const year = String(d.getUTCFullYear()).slice(-2);
        const hours = String(d.getUTCHours()).padStart(2, '0');
        const minutes = String(d.getUTCMinutes()).padStart(2, '0');
        return `${day}/${month}/${year} ${hours}:${minutes}`;
      })();
      labelMap[i] = timeLabel;
      const open = parseFloat(row[CONFIG.COLUMNS.OPEN]);
      const high = parseFloat(row[CONFIG.COLUMNS.HIGH]);
      const low = parseFloat(row[CONFIG.COLUMNS.LOW]);
      const close = parseFloat(row[CONFIG.COLUMNS.CLOSE]);
      if (![open, high, low, close].every(Number.isFinite)) continue;
      ohlcIndexed.push({ time: i, open, high, low, close });
    }

    const chart = LightweightCharts.createChart(c, {
      width: c.clientWidth,
      height: 400,
      layout: { background: { color: isDark ? '#161b22' : '#fff' }, textColor: isDark ? '#c9d1d9' : '#202124' },
      grid: { vertLines: { visible: false }, horzLines: { color: isDark ? '#30363d' : '#f1f3f4' } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: isDark ? '#30363d' : '#dadce0', autoScale: true, scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: isDark ? '#30363d' : '#dadce0', timeVisible: true, secondsVisible: false, rightOffset: 20, barSpacing: 12 },
      localization: {
        timeFormatter: (time) => {
          const k = Math.floor(Number(time));
          return labelMap[k] || '';
        }
      }
    });

    let __lc_isSnapping = false;
    chart.subscribeCrosshairMove((param) => {
      if (__lc_isSnapping) return;
      if (!param || param.time === undefined || param.time === null) return;
      const t = param.time;
      if (typeof t !== 'number') return;
      const snapped = Math.round(t);
      if (!Number.isFinite(snapped)) return;
      if (Math.abs(t - snapped) < 1e-9) return;
      __lc_isSnapping = true;
      try {
        chart.setCrosshairPosition({ time: snapped });
      } catch (err) {
        // ignore
      } finally {
        __lc_isSnapping = false;
      }
    });

    const cs = chart.addCandlestickSeries({
      upColor: '#089981',
      downColor: '#f23645',
      borderDownColor: '#f23645',
      borderUpColor: '#089981',
      wickDownColor: '#f23645',
      wickUpColor: '#089981',
      lastValueVisible: true,
      priceLineVisible: false
    });

    cs.setData(ohlcIndexed);

    this.addSupertrendSeries(chart, candles, 'LARGER', { indexed: true });
    this.addSupertrendSeries(chart, candles, 'SHORTER', { indexed: true });
    this.addBandSeries(chart, candles, { indexed: true });

    if (ohlcIndexed.length > 0) {
      setTimeout(() => {
        const n = ohlcIndexed.length;
        const lastIndex = n - 1;
        const from = Math.max(0, lastIndex - 29);
        const to = lastIndex + 1;
        try { chart.timeScale().setVisibleLogicalRange({ from, to }); } catch (e) {}
        try {
          if (typeof chart.timeScale().scrollToRealTime === 'function') chart.timeScale().scrollToRealTime();
          else if (typeof chart.timeScale().scrollToPosition === 'function') chart.timeScale().scrollToPosition(to, false);
        } catch (e) {}
      }, 80);
    }

    this.charts.set(containerId, chart);
    new ResizeObserver(e => {
      const r = e[0].contentRect;
      chart.applyOptions({ width: r.width, height: 400 });
    }).observe(c);
  }

  addSupertrendSeries(chart, candles, type, opts = {}) {
    const stCol = type === 'LARGER' ? CONFIG.COLUMNS.SUPERTREND_LARGER : CONFIG.COLUMNS.SUPERTREND_SHORTER;
    const dirCol = type === 'LARGER' ? CONFIG.COLUMNS.DIRECTION_LARGER : CONFIG.COLUMNS.DIRECTION_SHORTER;

    const rows = [];
    for (let i = 0, idx = 0; i < candles.length; i++) {
      const row = candles[i];
      const tsRaw = new Date(row[CONFIG.COLUMNS.TIMESTAMP]).getTime();
      if (!Number.isFinite(tsRaw)) continue;
      const val = parseFloat(row[stCol]);
      const dir = row[dirCol];
      if (!Number.isFinite(val)) continue;
      rows.push({ index: idx, value: val, dir });
      idx++;
    }
    if (rows.length === 0) return;

    const anchors = new Array(rows.length);
    for (let i = 0; i < rows.length; i++) {
      const t0 = rows[i].index;
      const t1 = i < rows.length - 1 ? rows[i + 1].index : (i > 0 ? rows[i].index + Math.max(1, rows[i].index - rows[i - 1].index) : rows[i].index + 1);
      anchors[i] = (t0 + t1) / 2;
    }

    let currentDir = null;
    let seg = [];
    const segments = [];
    let prevValue = null;

    for (let i = 0; i < rows.length; i++) {
      const anchor = anchors[i];
      const value = rows[i].value;
      const direction = rows[i].dir;

      if (currentDir === null || currentDir !== direction) {
        if (seg.length > 0) segments.push({ data: seg.slice(), dir: currentDir });
        seg = seg.length ? [seg[seg.length - 1]] : [];
        currentDir = direction;
      }

      if (prevValue !== null && prevValue !== value && seg.length > 0) seg.push({ time: anchor, value: prevValue });
      seg.push({ time: anchor, value });
      prevValue = value;

      if (i === rows.length - 1 && seg.length > 0) segments.push({ data: seg.slice(), dir: currentDir });
    }

    for (let s = 0; s < segments.length; s++) {
      const seg = segments[s];
      const pts = this.sanitizeAndSortPoints(seg.data);
      if (!pts.length) continue;
      const color = type === 'LARGER' ? (seg.dir === -1 ? '#34a853' : '#f23645') : (seg.dir === -1 ? '#FFD700' : '#1a73e8');
      const ls = chart.addLineSeries({
        color,
        lineWidth: 2,
        lineStyle: LightweightCharts.LineStyle.Solid,
        lineType: LightweightCharts.LineType.Simple,
        crosshairMarkerVisible: true,
        lastValueVisible: false,
        priceLineVisible: false
      });
      ls.setData(pts);
    }
  }

  addBandSeries(chart, candles, opts = {}) {
    const process = (col, dirCol, colorA, colorB) => {
      const rows = [];
      for (let i = 0, idx = 0; i < candles.length; i++) {
        const row = candles[i];
        const tsRaw = new Date(row[CONFIG.COLUMNS.TIMESTAMP]).getTime();
        if (!Number.isFinite(tsRaw)) continue;
        const v = parseFloat(row[col]);
        const d = row[dirCol];
        if (!Number.isFinite(v)) continue;
        rows.push({ index: idx, value: v, dir: d });
        idx++;
      }
      if (rows.length === 0) return;

      const anchors = new Array(rows.length);
      for (let i = 0; i < rows.length; i++) {
        const t0 = rows[i].index;
        const t1 = i < rows.length - 1 ? rows[i + 1].index : (i > 0 ? rows[i].index + Math.max(1, rows[i].index - rows[i - 1].index) : rows[i].index + 1);
        anchors[i] = (t0 + t1) / 2;
      }

      let op = null;
      let seg = [];
      const all = [];
      let prev = null;

      for (let i = 0; i < rows.length; i++) {
        const anchor = anchors[i];
        const val = rows[i].value;
        const d = rows[i].dir;
        const newOp = d === 1 ? colorA : colorB;

        if (op === null || op !== newOp) {
          if (seg.length > 0) all.push({ data: seg.slice(), op });
          seg = seg.length ? [seg[seg.length - 1]] : [];
          op = newOp;
          prev = null;
        }

        if (prev !== null && prev !== val && seg.length > 0) seg.push({ time: anchor, value: prev });
        seg.push({ time: anchor, value: val });
        prev = val;

        if (i === rows.length - 1 && seg.length > 0) all.push({ data: seg.slice(), op });
      }

      for (let k = 0; k < all.length; k++) {
        const s = all[k];
        const clean = this.sanitizeAndSortPoints(s.data);
        if (!clean.length) continue;
        const ls = chart.addLineSeries({
          color: s.op,
          lineWidth: 1,
          lineStyle: LightweightCharts.LineStyle.Solid,
          lineType: LightweightCharts.LineType.Simple,
          crosshairMarkerVisible: false,
          lastValueVisible: false,
          priceLineVisible: false
        });
        ls.setData(clean);
      }
    };

    process(CONFIG.COLUMNS.UPPERBAND_SHORTER, CONFIG.COLUMNS.DIRECTION_SHORTER, '#1a73e8FF', '#1a73e880');
    process(CONFIG.COLUMNS.LOWERBAND_SHORTER, CONFIG.COLUMNS.DIRECTION_SHORTER, '#FFD70080', '#FFD700FF');
  }


  clearAllCharts() {
    this.charts.forEach(c => { try { c.remove(); } catch {} });
    this.charts.clear();
    if (this.scrollListener) {
      window.removeEventListener('scroll', this.scrollListener);
      this.scrollListener = null;
    }
  }

  updateChartsTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    this.charts.forEach(chart => {
      chart.applyOptions({
        layout: { background: { color: isDark ? '#161b22' : '#fff' }, textColor: isDark ? '#c9d1d9' : '#202124' },
        grid: { horzLines: { color: isDark ? '#30363d' : '#f1f3f4' } },
        rightPriceScale: { borderColor: isDark ? '#30363d' : '#dadce0' },
        timeScale: { borderColor: isDark ? '#30363d' : '#dadce0' }
      });
    });
  }
}

const chartsManager = new ChartsManager();
