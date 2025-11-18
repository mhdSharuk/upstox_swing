"""
Chart Handler - Prepare and render TradingView lightweight charts
UPDATED: 
- Increased chart dimensions
- Added Long/Short filter
- Added Watchlist/Signals data source filter
- Added per-chart supertrend selector
- Reduced title font size
"""

import streamlit as st
import pandas as pd
from streamlit_lightweight_charts import renderLightweightCharts
import data_handler
import config


def prepare_chart_data(df, symbol, supertrend_col):
    """
    Prepare candle and supertrend data for a single symbol
    
    Args:
        df: Full dataframe with all symbols
        symbol: Symbol to chart
        supertrend_col: Supertrend column name (e.g., 'supertrend_st_125m_sma15')
    
    Returns:
        tuple: (candle_data, supertrend_data, direction)
    """
    # Filter data for this symbol
    symbol_df = df[df['trading_symbol'] == symbol].copy()
    
    if symbol_df.empty:
        return [], [], None
    
    # Sort by timestamp
    symbol_df = symbol_df.sort_values('timestamp')
    
    # Convert numeric columns
    for col in ['open', 'high', 'low', 'close', supertrend_col]:
        if col in symbol_df.columns:
            symbol_df[col] = pd.to_numeric(symbol_df[col], errors='coerce')
    
    # Convert timestamp to Unix timestamp (seconds)
    symbol_df['timestamp'] = pd.to_datetime(symbol_df['timestamp'])
    
    # Remove timezone info if present, then convert to Unix timestamp
    if symbol_df['timestamp'].dt.tz is not None:
        # Convert to UTC and remove timezone
        symbol_df['time'] = (symbol_df['timestamp'].dt.tz_convert('UTC')
                            .dt.tz_localize(None)
                            .astype('int64') // 10**9)
    else:
        symbol_df['time'] = symbol_df['timestamp'].astype('int64') // 10**9
    
    # Prepare candlestick data
    candle_data = []
    for _, row in symbol_df.iterrows():
        candle_data.append({
            'time': int(row['time']),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })
    
    # Prepare supertrend line data
    supertrend_data = []
    for _, row in symbol_df.iterrows():
        if pd.notna(row[supertrend_col]):
            supertrend_data.append({
                'time': int(row['time']),
                'value': float(row[supertrend_col])
            })
    
    # Get direction from last candle
    direction_col = supertrend_col.replace('supertrend_', 'direction_')
    direction = None
    if direction_col in symbol_df.columns:
        last_direction = symbol_df[direction_col].iloc[-1]
        if pd.notna(last_direction):
            direction = int(float(last_direction))
    
    return candle_data, supertrend_data, direction


def create_chart_config(symbol, candle_data, supertrend_data, direction, chart_width=680, chart_height=480):
    """
    Create lightweight-charts configuration for a single symbol
    
    Args:
        symbol: Symbol name
        candle_data: List of candlestick data points
        supertrend_data: List of supertrend line data points
        direction: 1 or -1 (supertrend direction)
        chart_width: Chart width in pixels
        chart_height: Chart height in pixels
    
    Returns:
        dict: Chart configuration
    """
    # Determine colors based on direction
    # Direction -1 = Long signal = Yellow
    # Direction 1 = Short signal = Blue
    if direction == -1:
        supertrend_color = '#FFA500'  # Yellow/Orange
        signal_type = "LONG"
    else:
        supertrend_color = '#2962FF'  # Blue
        signal_type = "SHORT"
    
    chart_config = {
        "width": chart_width,
        "height": chart_height,
        "layout": {
            "background": {
                "type": "solid",
                "color": "#0d1117"
            },
            "textColor": "#c9d1d9"
        },
        "grid": {
            "vertLines": {
                "color": "rgba(197, 203, 206, 0.1)"
            },
            "horzLines": {
                "color": "rgba(197, 203, 206, 0.1)"
            }
        },
        "crosshair": {
            "mode": 0
        },
        "priceScale": {
            "borderColor": "rgba(197, 203, 206, 0.2)"
        },
        "timeScale": {
            "borderColor": "rgba(197, 203, 206, 0.2)",
            "timeVisible": True,
            "secondsVisible": False
        }
    }
    
    # Candlestick series
    candlestick_series = {
        "type": "Candlestick",
        "data": candle_data,
        "options": {
            "upColor": "#26a69a",
            "downColor": "#ef5350",
            "borderVisible": False,
            "wickUpColor": "#26a69a",
            "wickDownColor": "#ef5350"
        }
    }
    
    # Supertrend line series
    supertrend_series = {
        "type": "Line",
        "data": supertrend_data,
        "options": {
            "color": supertrend_color,
            "lineWidth": 2,
            "title": f"Supertrend ({signal_type})"
        }
    }
    
    return {
        "chart": chart_config,
        "series": [candlestick_series, supertrend_series],
        "title": f"{symbol} - {signal_type}"
    }


def get_watchlist_symbols(timeframe, supertrend, signal_type_filter):
    """
    Get symbols from watchlist based on timeframe and filters
    
    Args:
        timeframe: 'Daily' or '125min'
        supertrend: Selected supertrend name
        signal_type_filter: 'Long', 'Short', or 'Both'
    
    Returns:
        list: List of symbols from watchlist
    """
    watchlist_data = data_handler.fetch_watchlist_data()
    
    if not watchlist_data:
        return []
    
    sheet_name = 'daily_signals' if timeframe == 'Daily' else '125min_signals'
    
    symbols = []
    for item in watchlist_data:
        # Match sheet and supertrend
        if item['sheet'] == sheet_name and item['supertrend'] == supertrend:
            # Apply signal type filter
            if signal_type_filter == 'Both':
                symbols.append(item['symbol'])
            elif signal_type_filter == item['type']:
                symbols.append(item['symbol'])
    
    return symbols


def render_single_chart(df, symbol, available_supertrends, default_supertrend, chart_index):
    """
    Render a single chart with supertrend selector
    
    Args:
        df: Full dataframe
        symbol: Symbol to chart
        available_supertrends: List of available supertrend configurations
        default_supertrend: Default supertrend to display
        chart_index: Unique index for this chart (for widget keys)
    """
    # Create unique key for this chart's selectbox
    select_key = f"st_select_{symbol}_{chart_index}"
    
    # Initialize session state ONLY if it doesn't exist (before widget creation)
    if select_key not in st.session_state:
        st.session_state[select_key] = default_supertrend
    
    # Get selected supertrend value from session state (widget manages it)
    selected_st = st.session_state.get(select_key, default_supertrend)
    
    # Prepare chart data with selected supertrend
    supertrend_col = f'supertrend_{selected_st}'
    candle_data, supertrend_data, direction = prepare_chart_data(
        df, symbol, supertrend_col
    )
    
    if candle_data and supertrend_data:
        # Determine signal type and emoji
        signal_type = "🟡 LONG" if direction == -1 else "🔵 SHORT"
        
        # Compact layout: Symbol and Supertrend selector on same line
        col_symbol, col_spacer, col_st = st.columns([2, 0.2, 1.8])
        
        with col_symbol:
            # Compact symbol display
            st.markdown(
                f"<p style='font-size:16px; margin:0; padding-top:8px;'><b>{signal_type} {symbol}</b></p>", 
                unsafe_allow_html=True
            )
        
        with col_st:
            # Compact supertrend selector
            st.selectbox(
                "ST",
                options=available_supertrends,
                index=available_supertrends.index(selected_st) if selected_st in available_supertrends else 0,
                key=select_key,
                label_visibility="collapsed"
            )
        
        # Create and render chart with auto-width
        chart_config = create_chart_config(
            symbol, 
            candle_data, 
            supertrend_data, 
            direction,
            chart_height=480,
            chart_width=850,    
        )
        
        # Render chart with unique key
        renderLightweightCharts([chart_config], f"chart_{symbol}_{chart_index}_{selected_st}")
    else:
        st.warning(f"No chart data available for {symbol}")


def render_charts_grid(df, supertrend_name, sector, industry, min_mcap, max_pct, min_flat, 
                       signal_type_filter, data_source, timeframe, available_supertrends):
    """
    Render charts in a 2-column grid for all filtered symbols with PAGINATION
    
    Args:
        df: Full dataframe
        supertrend_name: Supertrend name for filtering (e.g., 'st_125m_sma15')
        sector: Selected sector filter
        industry: Selected industry filter
        min_mcap: Minimum market cap filter
        max_pct: Maximum pct diff filter
        min_flat: Minimum flatbase filter
        signal_type_filter: 'Long', 'Short', or 'Both'
        data_source: 'Signals' or 'Watchlist'
        timeframe: 'Daily' or '125min'
        available_supertrends: List of available supertrend configurations
    """
    if df.empty:
        st.info("No data available for charts")
        return
    
    # Determine symbols based on data source
    if data_source == 'Watchlist':
        # Get symbols from watchlist
        symbols = get_watchlist_symbols(timeframe, supertrend_name, signal_type_filter)
        
        if not symbols:
            st.info("No symbols in watchlist matching the criteria")
            return
        
        data_source_text = "Watchlist"
    else:
        # Get symbols from signal filters
        # Get supertrend column
        supertrend_col = f'supertrend_{supertrend_name}'
        direction_col = f'direction_{supertrend_name}'
        pct_col = f'pct_diff_latest_{supertrend_name}'
        flat_col = f'flatbase_count_{supertrend_name}'
        
        # Check if columns exist
        required_cols = [supertrend_col, direction_col, pct_col, flat_col]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns: {missing_cols}")
            return
        
        # Get latest rows per symbol
        latest_df = data_handler.get_latest_rows_per_symbol(df)
        
        # Convert numeric columns
        latest_df['market_cap'] = pd.to_numeric(latest_df['market_cap'], errors='coerce')
        latest_df[pct_col] = pd.to_numeric(latest_df[pct_col], errors='coerce')
        latest_df[flat_col] = pd.to_numeric(latest_df[flat_col], errors='coerce')
        latest_df[direction_col] = pd.to_numeric(latest_df[direction_col], errors='coerce')
        
        # Apply filters
        filtered_df = latest_df.copy()
        
        # Sector filter
        if sector != 'All':
            filtered_df = filtered_df[filtered_df['sector'] == sector]
        
        # Industry filter
        if industry != 'All':
            filtered_df = filtered_df[filtered_df['industry'] == industry]
        
        # Market cap filter
        filtered_df = filtered_df[filtered_df['market_cap'] >= min_mcap]
        
        # Flatbase filter
        filtered_df = filtered_df[filtered_df[flat_col] >= min_flat]
        
        # Pct diff filter (absolute value)
        filtered_df = filtered_df[filtered_df[pct_col].abs() <= max_pct]
        
        # Signal type filter
        if signal_type_filter == 'Long':
            filtered_df = filtered_df[filtered_df[direction_col] == -1]
        elif signal_type_filter == 'Short':
            filtered_df = filtered_df[filtered_df[direction_col] == 1]
        # 'Both' means no direction filter
        
        # Get unique symbols
        symbols = filtered_df['trading_symbol'].unique().tolist()
        
        if not symbols:
            st.info("No symbols match the filter criteria")
            return
        
        data_source_text = "Signals"
    
    # PAGINATION SETUP
    # Initialize charts per page setting
    cpp_key = f'charts_per_page_{timeframe}'
    if cpp_key not in st.session_state:
        st.session_state[cpp_key] = 20
    
    # Show charts per page selector
    col_cpp, col_space = st.columns([1, 3])
    with col_cpp:
        charts_per_page = st.selectbox(
            "Charts per page",
            options=[10, 20, 50, 100],
            index=[10, 20, 50, 100].index(st.session_state[cpp_key]) if st.session_state[cpp_key] in [10, 20, 50, 100] else 1,
            key=cpp_key
        )
    
    total_symbols = len(symbols)
    
    # Show performance tip for large datasets
    if total_symbols > 100:
        st.info(f"💡 **Performance Tip:** You have {total_symbols} symbols. Use filters (Sector, Industry, Pct Diff, etc.) to narrow down results for faster loading.")
    
    total_pages = (total_symbols + charts_per_page - 1) // charts_per_page
    
    # Initialize pagination state
    page_key = f'chart_page_{timeframe}_{data_source}'
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    
    current_page = st.session_state[page_key]
    
    # Display pagination info and controls
    st.markdown("---")
    col_info, col_jump, col_nav = st.columns([2, 1, 1])
    
    with col_info:
        start_idx = (current_page - 1) * charts_per_page + 1
        end_idx = min(current_page * charts_per_page, total_symbols)
        st.caption(f"📊 {start_idx}-{end_idx} of {total_symbols} symbols | Page {current_page}/{total_pages}")
    
    with col_jump:
        jump_page = st.number_input(
            "Go to page",
            min_value=1,
            max_value=total_pages,
            value=current_page,
            step=1,
            key=f"jump_{timeframe}_{data_source}",
            label_visibility="collapsed"
        )
        if jump_page != current_page:
            st.session_state[page_key] = jump_page
            st.rerun()
    
    with col_nav:
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅️ Prev", disabled=(current_page == 1), use_container_width=True):
                st.session_state[page_key] = max(1, current_page - 1)
                st.rerun()
        with col_next:
            if st.button("Next ➡️", disabled=(current_page >= total_pages), use_container_width=True):
                st.session_state[page_key] = min(total_pages, current_page + 1)
                st.rerun()
    
    # Get symbols for current page
    start_idx = (current_page - 1) * charts_per_page
    end_idx = start_idx + charts_per_page
    page_symbols = symbols[start_idx:end_idx]
    
    st.markdown("---")
    
    # Render charts for current page only
    chart_index = start_idx  # Use actual index for unique keys
    for i in range(0, len(page_symbols), 2):
        col1, col2 = st.columns(2)
        
        # Left chart
        with col1:
            symbol = page_symbols[i]
            render_single_chart(df, symbol, available_supertrends, supertrend_name, chart_index)
            chart_index += 1
        
        # Right chart (if exists)
        if i + 1 < len(page_symbols):
            with col2:
                symbol = page_symbols[i + 1]
                render_single_chart(df, symbol, available_supertrends, supertrend_name, chart_index)
                chart_index += 1
        
        # Add minimal spacing between rows for compact layout
        st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    
    # Bottom pagination controls
    st.markdown("---")
    col_nav_bottom = st.columns([3, 1])[1]
    with col_nav_bottom:
        col_prev_b, col_next_b = st.columns(2)
        with col_prev_b:
            if st.button("⬅️", disabled=(current_page == 1), key="prev_bottom", use_container_width=True):
                st.session_state[page_key] = max(1, current_page - 1)
                st.rerun()
        with col_next_b:
            if st.button("➡️", disabled=(current_page >= total_pages), key="next_bottom", use_container_width=True):
                st.session_state[page_key] = min(total_pages, current_page + 1)
                st.rerun()


def render_chart_filters(prefix, df):
    """
    Render filters for charts tab
    
    Args:
        prefix: 'chart' prefix for session state keys
        df: DataFrame to extract filter options from
    
    Returns:
        dict: Dictionary of selected filter values
    """
    # Initialize session state for chart filters if not exists
    if f'{prefix}_timeframe' not in st.session_state:
        st.session_state[f'{prefix}_timeframe'] = 'Daily'
    if f'{prefix}_supertrend' not in st.session_state:
        st.session_state[f'{prefix}_supertrend'] = None
    if f'{prefix}_sector' not in st.session_state:
        st.session_state[f'{prefix}_sector'] = 'All'
    if f'{prefix}_industry' not in st.session_state:
        st.session_state[f'{prefix}_industry'] = 'All'
    if f'{prefix}_mcap' not in st.session_state:
        st.session_state[f'{prefix}_mcap'] = config.DEFAULT_MCAP
    if f'{prefix}_pct' not in st.session_state:
        st.session_state[f'{prefix}_pct'] = config.DEFAULT_PCT_DIFF
    if f'{prefix}_flat' not in st.session_state:
        st.session_state[f'{prefix}_flat'] = config.DEFAULT_FLATBASE
    if f'{prefix}_signal_type' not in st.session_state:
        st.session_state[f'{prefix}_signal_type'] = 'Both'
    if f'{prefix}_data_source' not in st.session_state:
        st.session_state[f'{prefix}_data_source'] = 'Signals'
    
    st.subheader("Chart Filters")
    
    # First row: Timeframe, Data Source, Signal Type
    col_tf, col_source, col_signal = st.columns(3)
    
    with col_tf:
        timeframe = st.selectbox(
            "Timeframe",
            options=['Daily', '125min'],
            index=['Daily', '125min'].index(st.session_state[f'{prefix}_timeframe']),
            key=f'{prefix}_timeframe_select'
        )
        st.session_state[f'{prefix}_timeframe'] = timeframe
    
    with col_source:
        data_source = st.selectbox(
            "Data Source",
            options=['Signals', 'Watchlist'],
            index=['Signals', 'Watchlist'].index(st.session_state[f'{prefix}_data_source']),
            key=f'{prefix}_data_source_select'
        )
        st.session_state[f'{prefix}_data_source'] = data_source
    
    with col_signal:
        signal_type = st.selectbox(
            "Signal Type",
            options=['Both', 'Long', 'Short'],
            index=['Both', 'Long', 'Short'].index(st.session_state[f'{prefix}_signal_type']),
            key=f'{prefix}_signal_type_select'
        )
        st.session_state[f'{prefix}_signal_type'] = signal_type
    
    # Load data based on selected timeframe
    sheet_name = config.DAILY_DATA_SHEET if timeframe == 'Daily' else config.MIN125_DATA_SHEET
    signal_type_key = 'daily' if timeframe == 'Daily' else '125min'
    
    with st.spinner(f"Loading {timeframe} data..."):
        df_loaded = data_handler.fetch_sheet_data(sheet_name)
    
    if df_loaded.empty:
        st.warning(f"No data available for {timeframe}")
        return None
    
    # Get filter options from loaded data
    supertrends = data_handler.get_supertrend_columns(df_loaded, signal_type_key)
    sectors = data_handler.get_sectors(df_loaded)
    industries = data_handler.get_industries(df_loaded)
    
    # Set default supertrend if not set
    if not st.session_state[f'{prefix}_supertrend'] and supertrends:
        st.session_state[f'{prefix}_supertrend'] = supertrends[0]
    
    # Second row: Main filters (only shown for 'Signals' data source)
    if data_source == 'Signals':
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            supertrend = st.selectbox(
                "Supertrend (Filter)",
                options=supertrends if supertrends else [''],
                index=supertrends.index(st.session_state[f'{prefix}_supertrend']) if st.session_state[f'{prefix}_supertrend'] in supertrends else 0,
                key=f'{prefix}_supertrend_select',
                help="Supertrend used for filtering symbols. Each chart can show different supertrends."
            )
            st.session_state[f'{prefix}_supertrend'] = supertrend
        
        with col2:
            sector = st.selectbox(
                "Sector",
                options=sectors,
                index=sectors.index(st.session_state[f'{prefix}_sector']) if st.session_state[f'{prefix}_sector'] in sectors else 0,
                key=f'{prefix}_sector_select'
            )
            st.session_state[f'{prefix}_sector'] = sector
        
        with col3:
            industry = st.selectbox(
                "Industry",
                options=industries,
                index=industries.index(st.session_state[f'{prefix}_industry']) if st.session_state[f'{prefix}_industry'] in industries else 0,
                key=f'{prefix}_industry_select'
            )
            st.session_state[f'{prefix}_industry'] = industry
        
        with col4:
            mcap = st.number_input(
                "Market Cap ≥",
                min_value=0,
                value=st.session_state[f'{prefix}_mcap'],
                step=1000,
                key=f'{prefix}_mcap_input'
            )
            st.session_state[f'{prefix}_mcap'] = mcap
        
        with col5:
            pct = st.number_input(
                "Pct Diff ≤",
                min_value=0.0,
                value=st.session_state[f'{prefix}_pct'],
                step=0.1,
                format="%.1f",
                key=f'{prefix}_pct_input'
            )
            st.session_state[f'{prefix}_pct'] = pct
        
        with col6:
            flat = st.number_input(
                "Flatbase ≥",
                min_value=0,
                value=st.session_state[f'{prefix}_flat'],
                step=1,
                key=f'{prefix}_flat_input'
            )
            st.session_state[f'{prefix}_flat'] = flat
    else:
        # For Watchlist, still need supertrend for filtering
        supertrend = st.selectbox(
            "Supertrend",
            options=supertrends if supertrends else [''],
            index=supertrends.index(st.session_state[f'{prefix}_supertrend']) if st.session_state[f'{prefix}_supertrend'] in supertrends else 0,
            key=f'{prefix}_supertrend_select',
            help="Filter watchlist by this supertrend configuration"
        )
        st.session_state[f'{prefix}_supertrend'] = supertrend
        
        # Set defaults for unused filters
        sector = 'All'
        industry = 'All'
        mcap = config.DEFAULT_MCAP
        pct = config.DEFAULT_PCT_DIFF
        flat = config.DEFAULT_FLATBASE
    
    return {
        'df': df_loaded,
        'timeframe': timeframe,
        'supertrend': supertrend,
        'sector': sector,
        'industry': industry,
        'mcap': mcap,
        'pct': pct,
        'flat': flat,
        'signal_type': signal_type,
        'data_source': data_source,
        'available_supertrends': supertrends
    }