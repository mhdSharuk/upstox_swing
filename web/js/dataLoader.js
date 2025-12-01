/**
 * Data Loader Module - Simplified for 125min Data Only
 * Uses hyparquet with IndexedDB caching
 */

class DataLoader {
  constructor() {
    this.data = null;
    this.isLoading = false;
  }

  /**
   * Load parquet file from Supabase with IndexedDB caching
   * @param {boolean} forceRefresh - Skip cache and download fresh data
   * @returns {Promise<Array>} Parsed data as array of objects
   */
  async loadData(forceRefresh = false) {
    try {
      if (typeof CONFIG === 'undefined') {
        throw new Error('CONFIG is not defined. Make sure config.js is loaded first.');
      }
      
      console.log('📥 Loading 125min data from:', CONFIG.PARQUET_URL);

      this.isLoading = true;
      
      let arrayBuffer;
      
      if (!forceRefresh) {
        // Try to get from IndexedDB cache first
        const cachedBuffer = await this.getFromCache();
        if (cachedBuffer) {
          console.log('✓ Loaded from browser cache (instant!)');
          arrayBuffer = cachedBuffer;
        }
      }
      
      if (!arrayBuffer) {
        console.log('📥 Downloading from Supabase...');
        
        // Fetch with progress
        const response = await fetch(CONFIG.PARQUET_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentLength = response.headers.get('content-length');
        const fileSize = contentLength ? parseInt(contentLength) : 0;
        console.log(`File size: ${(fileSize / 1024 / 1024).toFixed(2)} MB`);
        
        const reader = response.body.getReader();
        const chunks = [];
        let receivedLength = 0;
        let lastLog = 0;
        
        while(true) {
          const {done, value} = await reader.read();
          if (done) break;
          
          chunks.push(value);
          receivedLength += value.length;
          
          // Log every 10%
          if (fileSize > 0) {
            const percent = Math.floor((receivedLength / fileSize) * 100);
            if (percent >= lastLog + 10) {
              console.log(`Downloaded: ${percent}% (${(receivedLength / 1024 / 1024).toFixed(2)} MB)`);
              lastLog = percent;
            }
          }
        }
        
        // Combine chunks
        const combinedArray = new Uint8Array(receivedLength);
        let position = 0;
        for(let chunk of chunks) {
          combinedArray.set(chunk, position);
          position += chunk.length;
        }
        
        arrayBuffer = combinedArray.buffer;
        console.log(`✓ Downloaded: ${(receivedLength / 1024 / 1024).toFixed(2)} MB`);
        
        // Save to cache
        await this.saveToCache(arrayBuffer);
        console.log('✓ Saved to browser cache');
      }
      
      // Parse parquet file with hyparquet
      console.log('✓ Parsing parquet data...');
      
      const [{ parquetRead }, { compressors }] = await Promise.all([
        import('https://cdn.jsdelivr.net/npm/hyparquet@1.4.1/+esm'),
        import('https://cdn.jsdelivr.net/npm/hyparquet-compressors@1.1.1/+esm')
      ]);
      
      const data = await new Promise((resolve, reject) => {
        parquetRead({
          file: arrayBuffer,
          compressors,
          rowFormat: 'object',
          onComplete: (rows) => resolve(rows),
          onError: (error) => reject(error)
        });
      });
      
      console.log(`✓ Parsed ${data.length} rows`);
      
      if (data.length > 0) {
        console.log('Sample row:', data[0]);
        console.log('Available columns:', Object.keys(data[0]));
      }
      
      this.data = data;
      this.isLoading = false;
      return data;
      
    } catch (error) {
      this.isLoading = false;
      console.error('❌ Error loading data:', error);
      throw error;
    }
  }

  /**
   * Get cached parquet file from IndexedDB
   * @returns {Promise<ArrayBuffer|null>}
   */
  async getFromCache() {
    return new Promise((resolve) => {
      const request = indexedDB.open('ParquetCache', 1);
      
      request.onerror = () => resolve(null);
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains('files')) {
          db.createObjectStore('files');
        }
      };
      
      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(['files'], 'readonly');
        const store = transaction.objectStore('files');
        const getRequest = store.get('125min');
        
        getRequest.onsuccess = () => resolve(getRequest.result || null);
        getRequest.onerror = () => resolve(null);
      };
    });
  }

  /**
   * Save parquet file to IndexedDB cache
   * @param {ArrayBuffer} arrayBuffer
   * @returns {Promise<void>}
   */
  async saveToCache(arrayBuffer) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ParquetCache', 1);
      
      request.onerror = () => reject(new Error('Failed to open IndexedDB'));
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains('files')) {
          db.createObjectStore('files');
        }
      };
      
      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(['files'], 'readwrite');
        const store = transaction.objectStore('files');
        const putRequest = store.put(arrayBuffer, '125min');
        
        putRequest.onsuccess = () => resolve();
        putRequest.onerror = () => reject(new Error('Failed to save to cache'));
      };
    });
  }

  /**
   * Clear cached data
   * @returns {Promise<void>}
   */
  async clearCache() {
    return new Promise((resolve) => {
      const request = indexedDB.open('ParquetCache', 1);
      
      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(['files'], 'readwrite');
        const store = transaction.objectStore('files');
        const clearRequest = store.clear();
        
        clearRequest.onsuccess = () => {
          console.log('✓ Cache cleared');
          resolve();
        };
      };
      
      request.onerror = () => resolve();
    });
  }

  /**
   * Get cached data or load if not available
   * @param {boolean} forceRefresh - Skip cache
   * @returns {Promise<Array>}
   */
  async getData(forceRefresh = false) {
    if (forceRefresh || !this.data) {
      return await this.loadData(forceRefresh);
    }
    return this.data;
  }

  /**
   * Group data by symbol and sort by timestamp
   * @returns {Map<string, Array>} Map of symbol -> sorted candles
   */
  getDataBySymbol() {
    if (!this.data) return new Map();
    
    const bySymbol = new Map();
    
    this.data.forEach(row => {
      const symbol = row[CONFIG.COLUMNS.SYMBOL];
      if (!symbol) return;
      
      if (!bySymbol.has(symbol)) {
        bySymbol.set(symbol, []);
      }
      bySymbol.get(symbol).push(row);
    });
    
    // Sort each symbol's candles by timestamp
    bySymbol.forEach((candles, symbol) => {
      candles.sort((a, b) => new Date(a[CONFIG.COLUMNS.TIMESTAMP]) - new Date(b[CONFIG.COLUMNS.TIMESTAMP]));
    });
    
    return bySymbol;
  }

  /**
   * Get latest candle for each symbol
   * @returns {Map<string, Object>} Map of symbol -> latest candle
   */
  getLatestCandles() {
    const bySymbol = this.getDataBySymbol();
    const latest = new Map();
    
    bySymbol.forEach((candles, symbol) => {
      if (candles.length > 0) {
        latest.set(symbol, candles[candles.length - 1]);
      }
    });
    
    console.log(`Found latest candles for ${latest.size} symbols`);
    return latest;
  }
}

// Create global instance
const dataLoader = new DataLoader();
console.log('✅ DataLoader initialized');