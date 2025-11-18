/**
 * Data Loader Module - FINAL VERSION
 * Uses hyparquet with rowFormat: 'object' for direct row-oriented data
 */

class DataLoader {
  constructor() {
    this.dailyData = null;
    this.min125Data = null;
    this.isLoading = {
      daily: false,
      min125: false
    };
  }

  /**
   * Load parquet file from Supabase with IndexedDB caching
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {Promise<Array>} Parsed data as array of objects
   */
  async loadParquetData(timeframe) {
    try {
      if (typeof CONFIG === 'undefined') {
        throw new Error('CONFIG is not defined. Make sure config.js is loaded before dataLoader.js');
      }
      
      const url = timeframe === 'daily' ? CONFIG.PARQUET_URLS.DAILY : CONFIG.PARQUET_URLS.MIN_125;
      
      console.log(`📥 Loading ${timeframe} data from:`, url);

      if (CONFIG.SUPABASE_URL === 'YOUR_SUPABASE_URL_HERE') {
        throw new Error('Please configure SUPABASE_URL in js/config.js');
      }

      this.isLoading[timeframe] = true;
      
      // Try to get from IndexedDB cache first
      const cachedBuffer = await this.getFromCache(timeframe);
      let arrayBuffer;
      
      if (cachedBuffer) {
        console.log(`✓ Loaded ${timeframe} from browser cache (instant!)`);
        arrayBuffer = cachedBuffer;
      } else {
        console.log(`📥 Downloading ${timeframe} for first time...`);
        
        // Fetch with progress
        const response = await fetch(url);
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
        console.log(`✓ Downloaded ${timeframe}: ${(receivedLength / 1024 / 1024).toFixed(2)} MB`);
        
        // Save to IndexedDB cache
        await this.saveToCache(timeframe, arrayBuffer);
        console.log(`✓ Saved ${timeframe} to browser cache`);
      }
      
      // Use hyparquet to parse parquet file with rowFormat: 'object'
      console.log(`✓ Parsing ${timeframe} data with hyparquet...`);
      
      // Import hyparquet with compression support
      const [{ parquetRead }, { compressors }] = await Promise.all([
        import('https://cdn.jsdelivr.net/npm/hyparquet@1.4.1/+esm'),
        import('https://cdn.jsdelivr.net/npm/hyparquet-compressors@1.1.1/+esm')
      ]);
      
      // Parse parquet file - with rowFormat: 'object' to get array of objects directly
      const data = await new Promise((resolve, reject) => {
        parquetRead({
          file: arrayBuffer,
          compressors,
          rowFormat: 'object', // ← This returns array of objects!
          onComplete: (rows) => resolve(rows),
          onError: (error) => reject(error)
        });
      });
      
      console.log(`✓ Parsed ${data.length} rows as objects`);
      
      // Log sample row to verify structure
      if (data.length > 0) {
        console.log('Sample row:', data[0]);
        console.log('Available columns:', Object.keys(data[0]));
      }
      
      // Cache the data
      if (timeframe === 'daily') {
        this.dailyData = data;
      } else {
        this.min125Data = data;
      }
      
      this.isLoading[timeframe] = false;
      return data;
      
    } catch (error) {
      this.isLoading[timeframe] = false;
      console.error(`❌ Error loading ${timeframe} data:`, error);
      console.error('Error details:', error.stack);
      throw error;
    }
  }

  /**
   * Get parquet file from IndexedDB cache
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {Promise<ArrayBuffer|null>} Cached buffer or null
   */
  async getFromCache(timeframe) {
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
        const getRequest = store.get(timeframe);
        
        getRequest.onsuccess = () => resolve(getRequest.result || null);
        getRequest.onerror = () => resolve(null);
      };
    });
  }

  /**
   * Save parquet file to IndexedDB cache
   * @param {string} timeframe - 'daily' or 'min125'
   * @param {ArrayBuffer} buffer - File buffer
   */
  async saveToCache(timeframe, buffer) {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ParquetCache', 1);
      
      request.onerror = () => reject(new Error('IndexedDB error'));
      
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
        store.put(buffer, timeframe);
        
        transaction.oncomplete = () => resolve();
        transaction.onerror = () => reject(new Error('Cache save failed'));
      };
    });
  }

  /**
   * Clear all cached parquet files
   */
  async clearCache() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('ParquetCache', 1);
      
      request.onsuccess = (event) => {
        const db = event.target.result;
        const transaction = db.transaction(['files'], 'readwrite');
        const store = transaction.objectStore('files');
        store.clear();
        
        transaction.oncomplete = () => {
          console.log('✓ Cache cleared');
          resolve();
        };
        transaction.onerror = () => reject(new Error('Cache clear failed'));
      };
    });
  }

  /**
   * Get data for specific timeframe (loads if not cached)
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {Promise<Array>} Data array
   */
  async getData(timeframe) {
    if (timeframe === 'daily') {
      if (!this.dailyData) {
        return await this.loadParquetData('daily');
      }
      return this.dailyData;
    } else {
      if (!this.min125Data) {
        return await this.loadParquetData('min125');
      }
      return this.min125Data;
    }
  }

  /**
   * Force refresh data (clear cache and reload)
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {Promise<Array>} Fresh data
   */
  async refreshData(timeframe) {
    if (timeframe === 'daily') {
      this.dailyData = null;
    } else {
      this.min125Data = null;
    }
    return await this.getData(timeframe);
  }

  /**
   * Get unique values for a column (for filter dropdowns)
   * @param {Array} data - Data array
   * @param {string} column - Column name
   * @returns {Array} Sorted unique values
   */
  getUniqueValues(data, column) {
    const values = new Set();
    data.forEach(row => {
      if (row[column] !== null && row[column] !== undefined && row[column] !== '') {
        values.add(row[column]);
      }
    });
    const uniqueArray = Array.from(values).sort();
    console.log(`Found ${uniqueArray.length} unique values for ${column}:`, uniqueArray.slice(0, 10));
    return uniqueArray;
  }

  /**
   * Get available supertrend columns for a timeframe
   * @param {string} timeframe - 'daily' or 'min125'
   * @returns {Array} Array of supertrend config objects
   */
  getSupertrendConfigs(timeframe) {
    return timeframe === 'daily' ? CONFIG.SUPERTRENDS.DAILY : CONFIG.SUPERTRENDS.MIN_125;
  }

  /**
   * Get latest candle for each symbol (for signal detection)
   * @param {Array} data - Full data array
   * @returns {Map} Map of symbol -> latest row
   */
  getLatestCandles(data) {
    const latestMap = new Map();
    
    console.log(`Processing ${data.length} rows to find latest candles...`);
    
    // Group by symbol and get latest timestamp
    data.forEach(row => {
      const symbol = row.trading_symbol;
      if (!symbol) {
        console.warn('Row missing trading_symbol:', row);
        return;
      }
      
      if (!latestMap.has(symbol)) {
        latestMap.set(symbol, row);
      } else {
        const existing = latestMap.get(symbol);
        const rowTime = new Date(row.timestamp);
        const existingTime = new Date(existing.timestamp);
        
        if (rowTime > existingTime) {
          latestMap.set(symbol, row);
        }
      }
    });
    
    console.log(`Found latest candles for ${latestMap.size} symbols`);
    
    // Log sample of latest candles for debugging
    const sampleSymbol = Array.from(latestMap.keys())[0];
    if (sampleSymbol) {
      console.log(`Sample latest candle (${sampleSymbol}):`, latestMap.get(sampleSymbol));
    }
    
    return latestMap;
  }

  /**
   * Get all candles for a specific symbol
   * @param {Array} data - Full data array
   * @param {string} symbol - Trading symbol
   * @returns {Array} All candles for the symbol, sorted by timestamp
   */
  getSymbolCandles(data, symbol) {
    return data
      .filter(row => row.trading_symbol === symbol)
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }
}

// Create global instance
const dataLoader = new DataLoader();