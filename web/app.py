"""
Signal Tracker - Streamlit Application
MASSIVE TABLE FONTS for easy reading
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

import config
import data_handler
import watchlist_manager
import utils


# Page configuration
st.set_page_config(
    page_title="Signal Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS with MASSIVE TABLE FONTS
st.markdown("""
<style>
    /* Reduce padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* EXTRA LARGE HEADERS */
    h1 {
        font-size: 48px !important;
        font-weight: 600 !important;
        margin-bottom: 1.5rem !important;
    }
    
    h2 {
        font-size: 32px !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-size: 26px !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    
    /* EXTRA LARGE LABELS */
    label {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
    
    /* EXTRA LARGE INPUT TEXT */
    input, select, textarea {
        font-size: 20px !important;
        padding: 12px !important;
        height: 50px !important;
    }
    
    /* EXTRA LARGE BUTTON TEXT */
    .stButton button {
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 14px 24px !important;
        height: 55px !important;
    }
    
    /* ===== MASSIVE TABLE FONTS ===== */
    .dataframe td {
        text-align: center !important;
        font-size: 28px !important;
        padding: 20px 16px !important;
        font-weight: 600 !important;
        line-height: 1.5 !important;
    }
    
    .dataframe th {
        text-align: center !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        padding: 20px 16px !important;
        line-height: 1.5 !important;
    }
    
    /* Make ALL table text visible */
    table, tbody, thead, tr, td, th {
        font-size: 28px !important;
    }
    
    /* Target data editor cells specifically */
    [data-testid="stDataFrame"] td {
        font-size: 28px !important;
    }
    
    [data-testid="stDataFrame"] th {
        font-size: 24px !important;
    }
    
    /* Force cell content to be large */
    .dataframe td > div,
    .dataframe th > div,
    [data-testid="stDataFrame"] td > div,
    [data-testid="stDataFrame"] th > div {
        font-size: 28px !important;
    }
    
    /* Narrow checkbox column */
    .dataframe td:first-child,
    .dataframe th:first-child {
        max-width: 70px !important;
        width: 70px !important;
    }
    
    /* EXTRA LARGE CHECKBOX */
    input[type="checkbox"] {
        width: 28px !important;
        height: 28px !important;
        cursor: pointer !important;
    }
    
    /* EXTRA LARGE GENERAL TEXT */
    .stMarkdown, .stText, p, div {
        font-size: 20px !important;
    }
    
    /* EXTRA LARGE CAPTIONS */
    .stCaptionContainer, .stCaption {
        font-size: 18px !important;
    }
    
    /* EXTRA LARGE TAB TEXT */
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
        font-weight: 600 !important;
        padding: 16px 32px !important;
    }
    
    /* EXTRA LARGE TOAST NOTIFICATIONS */
    .stToast {
        font-size: 20px !important;
    }
    
    /* EXTRA LARGE NUMBER INPUTS */
    .stNumberInput input {
        font-size: 20px !important;
    }
    
    /* EXTRA LARGE SELECT BOXES */
    .stSelectbox select {
        font-size: 20px !important;
    }
    
    /* EXTRA LARGE DROPDOWN OPTIONS */
    [role="option"] {
        font-size: 20px !important;
        padding: 12px !important;
    }
    
    /* EXTRA LARGE INFO/WARNING MESSAGES */
    .stAlert {
        font-size: 20px !important;
    }
    
    /* EXTRA LARGE SPINNER TEXT */
    .stSpinner > div {
        font-size: 20px !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'daily_supertrend' not in st.session_state:
        st.session_state.daily_supertrend = None
    if 'daily_sector' not in st.session_state:
        st.session_state.daily_sector = 'All'
    if 'daily_industry' not in st.session_state:
        st.session_state.daily_industry = 'All'
    if 'daily_mcap' not in st.session_state:
        st.session_state.daily_mcap = config.DEFAULT_MCAP
    if 'daily_pct' not in st.session_state:
        st.session_state.daily_pct = config.DEFAULT_PCT_DIFF
    if 'daily_flat' not in st.session_state:
        st.session_state.daily_flat = config.DEFAULT_FLATBASE
    
    if 'min125_supertrend' not in st.session_state:
        st.session_state.min125_supertrend = None
    if 'min125_sector' not in st.session_state:
        st.session_state.min125_sector = 'All'
    if 'min125_industry' not in st.session_state:
        st.session_state.min125_industry = 'All'
    if 'min125_mcap' not in st.session_state:
        st.session_state.min125_mcap = config.DEFAULT_MCAP
    if 'min125_pct' not in st.session_state:
        st.session_state.min125_pct = config.DEFAULT_PCT_DIFF
    if 'min125_flat' not in st.session_state:
        st.session_state.min125_flat = config.DEFAULT_FLATBASE
    
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None


def render_header():
    """Render application header"""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📊 Signal Tracker")
    with col2:
        if st.button("🔄 Refresh All", use_container_width=True):
            data_handler.clear_cache()
            st.rerun()


def render_filters(prefix, df):
    """Render filter section"""
    signal_type = 'daily' if prefix == 'daily' else '125min'
    
    # Get filter options
    supertrends = data_handler.get_supertrend_columns(df, signal_type)
    sectors = data_handler.get_sectors(df)
    industries = data_handler.get_industries(df)
    
    # Set default supertrend if not set
    if not st.session_state[f'{prefix}_supertrend'] and supertrends:
        st.session_state[f'{prefix}_supertrend'] = supertrends[0]
    
    st.subheader("Filters")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        supertrend = st.selectbox(
            "Supertrend",
            options=supertrends if supertrends else [''],
            index=supertrends.index(st.session_state[f'{prefix}_supertrend']) if st.session_state[f'{prefix}_supertrend'] in supertrends else 0,
            key=f'{prefix}_supertrend_select'
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
    
    # Refresh button and timestamp
    col_btn, col_time = st.columns([1, 5])
    with col_btn:
        if st.button("🔄 Refresh", key=f'{prefix}_refresh'):
            data_handler.clear_cache()
            st.rerun()
    
    with col_time:
        if st.session_state.last_refresh:
            st.caption(f"Last updated: {st.session_state.last_refresh}")


def render_signal_table_with_watchlist(df, signal_type, sheet_name, supertrend):
    """Render signal table with watchlist checkboxes"""
    if df.empty:
        st.info(f"No {signal_type.lower()} signals found")
        return
    
    # Load watchlist data
    watchlist_data = data_handler.fetch_watchlist_data()
    
    # Create a copy for display with checkbox column
    display_df = df.copy()
    
    # Convert pandas types to native Python types
    display_df['Close'] = display_df['Close'].astype(float)
    display_df['LTP %'] = display_df['LTP %'].astype(float)
    display_df['Pct Diff'] = display_df['Pct Diff'].astype(float)
    display_df['Flatbase'] = display_df['Flatbase'].astype(int)
    
    # Add checkbox state based on watchlist
    display_df.insert(0, 'Add', False)
    
    for idx, row in display_df.iterrows():
        symbol = row['Symbol']
        is_checked = watchlist_manager.is_in_watchlist(
            symbol, sheet_name, supertrend, signal_type, watchlist_data
        )
        display_df.at[idx, 'Add'] = is_checked
    
    # Configure column display
    column_config = {
        "Add": st.column_config.CheckboxColumn(
            "Add",
            help="Add to watchlist",
            default=False,
            width="small"
        ),
        "Symbol": st.column_config.TextColumn("Symbol", width="medium"),
        "Close": st.column_config.NumberColumn("Close", format="%.2f", width="small"),
        "LTP %": st.column_config.NumberColumn("LTP %", format="%.2f", width="small"),
        "Pct Diff": st.column_config.NumberColumn("Pct Diff", format="%.2f", width="small"),
        "Flatbase": st.column_config.NumberColumn("Flatbase", format="%d", width="small"),
    }
    
    # Display editable dataframe
    edited_df = st.data_editor(
        display_df[['Add', 'Symbol', 'Close', 'LTP %', 'Pct Diff', 'Flatbase']],
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key=f"{sheet_name}_{signal_type}_{supertrend}_table"
    )
    
    # Detect changes and update watchlist
    for idx in range(len(edited_df)):
        original_checked = display_df.iloc[idx]['Add']
        new_checked = edited_df.iloc[idx]['Add']
        
        if original_checked != new_checked:
            symbol = edited_df.iloc[idx]['Symbol']
            pct = float(display_df.iloc[idx]['Pct Diff'])
            flatbase = int(display_df.iloc[idx]['Flatbase'])
            
            if new_checked:
                success = watchlist_manager.add_to_watchlist(
                    symbol, sheet_name, supertrend, signal_type, pct, flatbase
                )
                if success:
                    st.toast(f"✅ Added {symbol}", icon="✅")
                    data_handler.clear_watchlist_cache_only()
                    st.rerun()
            else:
                success = watchlist_manager.remove_from_watchlist(
                    symbol, sheet_name, supertrend, signal_type
                )
                if success:
                    st.toast(f"❌ Removed {symbol}", icon="❌")
                    data_handler.clear_watchlist_cache_only()
                    st.rerun()


def render_daily_signals():
    """Render Daily Signals tab"""
    with st.spinner("Loading daily signals..."):
        df = data_handler.fetch_sheet_data(config.DAILY_DATA_SHEET)
    
    render_filters('daily', df)
    
    if df.empty:
        st.warning("No data available in daily_data sheet")
        return
    
    supertrend = st.session_state.daily_supertrend
    sector = st.session_state.daily_sector
    industry = st.session_state.daily_industry
    mcap = st.session_state.daily_mcap
    pct = st.session_state.daily_pct
    flat = st.session_state.daily_flat
    
    long_signals, short_signals = data_handler.process_signals(
        df, supertrend, sector, industry, mcap, pct, flat
    )
    
    st.session_state.last_refresh = datetime.now().strftime('%H:%M:%S')
    
    # Display signals side by side
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🟢 Long Signals ({len(long_signals)})")
        render_signal_table_with_watchlist(long_signals, 'Long', 'daily_signals', supertrend)
    
    with col2:
        st.subheader(f"🔴 Short Signals ({len(short_signals)})")
        render_signal_table_with_watchlist(short_signals, 'Short', 'daily_signals', supertrend)


def render_125min_signals():
    """Render 125min Signals tab"""
    with st.spinner("Loading 125min signals..."):
        df = data_handler.fetch_sheet_data(config.MIN125_DATA_SHEET)
    
    render_filters('min125', df)
    
    if df.empty:
        st.warning("No data available in 125min_data sheet")
        return
    
    supertrend = st.session_state.min125_supertrend
    sector = st.session_state.min125_sector
    industry = st.session_state.min125_industry
    mcap = st.session_state.min125_mcap
    pct = st.session_state.min125_pct
    flat = st.session_state.min125_flat
    
    long_signals, short_signals = data_handler.process_signals(
        df, supertrend, sector, industry, mcap, pct, flat
    )
    
    st.session_state.last_refresh = datetime.now().strftime('%H:%M:%S')
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🟢 Long Signals ({len(long_signals)})")
        render_signal_table_with_watchlist(long_signals, 'Long', '125min_signals', supertrend)
    
    with col2:
        st.subheader(f"🔴 Short Signals ({len(short_signals)})")
        render_signal_table_with_watchlist(short_signals, 'Short', '125min_signals', supertrend)


def render_watchlist():
    """Render Watchlist tab"""
    st.subheader("📌 Watchlist")
    
    col_btn, col_time = st.columns([1, 5])
    with col_btn:
        if st.button("🔄 Refresh Watchlist", use_container_width=True):
            data_handler.clear_cache()
            st.rerun()
    
    with col_time:
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    with st.spinner("Loading watchlist..."):
        watchlist_data = data_handler.fetch_watchlist_data()
    
    if not watchlist_data:
        st.info("No items in watchlist. Add items from Daily or 125min signals tabs.")
        return
    
    watchlist_df = watchlist_manager.get_watchlist_as_dataframe(watchlist_data)
    watchlist_df.insert(0, 'Remove', False)
    
    column_config = {
        "Remove": st.column_config.CheckboxColumn("Remove", help="Remove from watchlist", default=False, width="small"),
        "Symbol": st.column_config.TextColumn("Symbol", width="small"),
        "Sheet": st.column_config.TextColumn("Sheet", width="medium"),
        "Supertrend": st.column_config.TextColumn("Supertrend", width="medium"),
        "Type": st.column_config.TextColumn("Type", width="small"),
        "Pct Diff": st.column_config.TextColumn("Pct Diff", width="small"),
        "Flatbase": st.column_config.TextColumn("Flatbase", width="small"),
        "Date Added": st.column_config.TextColumn("Date Added", width="medium"),
    }
    
    edited_watchlist = st.data_editor(
        watchlist_df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        key="watchlist_table"
    )
    
    for idx in range(len(edited_watchlist)):
        if edited_watchlist.iloc[idx]['Remove']:
            item = watchlist_data[idx]
            success = watchlist_manager.remove_from_watchlist(
                item['symbol'], item['sheet'], item['supertrend'], item['type']
            )
            if success:
                st.toast(f"❌ Removed {item['symbol']}", icon="❌")
                data_handler.clear_watchlist_cache_only()
                st.rerun()


def main():
    """Main application"""
    init_session_state()
    
    # Auto-refresh during market hours
    if utils.is_market_hours():
        st_autorefresh(interval=config.AUTO_REFRESH_INTERVAL, key="auto_refresh")
    
    render_header()
    
    tab1, tab2, tab3 = st.tabs(["Daily Signals", "125min Signals", "Watchlist"])
    
    with tab1:
        render_daily_signals()
    
    with tab2:
        render_125min_signals()
    
    with tab3:
        render_watchlist()


if __name__ == "__main__":
    main()