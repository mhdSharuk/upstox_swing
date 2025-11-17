"""
Signal Tracker - Streamlit Application
Using st.data_editor with checkbox column for watchlist management and LARGE FONTS
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

# CSS for UI elements
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
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
    
    label {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
    
    input, select, textarea {
        font-size: 20px !important;
        padding: 12px !important;
        height: 50px !important;
    }
    
    .stButton button {
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 14px 24px !important;
        height: 55px !important;
    }
    
    .stMarkdown, .stText, p, div {
        font-size: 20px !important;
    }
    
    .stCaptionContainer, .stCaption {
        font-size: 18px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
        font-weight: 600 !important;
        padding: 16px 32px !important;
    }
    
    .stToast {
        font-size: 20px !important;
    }
    
    .stNumberInput input {
        font-size: 20px !important;
    }
    
    .stSelectbox select {
        font-size: 20px !important;
    }
    
    [role="option"] {
        font-size: 20px !important;
        padding: 12px !important;
    }
    
    .stAlert {
        font-size: 20px !important;
    }
    
    .stSpinner > div {
        font-size: 20px !important;
    }
    
    /* Larger fonts for data_editor tables */
    .stDataFrame, [data-testid="stDataFrame"] {
        font-size: 20px !important;
    }
    
    [data-testid="stDataFrame"] table {
        font-size: 20px !important;
    }
    
    [data-testid="stDataFrame"] th {
        font-size: 22px !important;
        font-weight: 700 !important;
        padding: 12px !important;
    }
    
    [data-testid="stDataFrame"] td {
        font-size: 20px !important;
        font-weight: 600 !important;
        padding: 10px !important;
    }
    
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
    """Render signal table with checkboxes for watchlist management and LARGE FONTS"""
    if df.empty:
        st.info(f"No {signal_type.lower()} signals found")
        return
    
    # Load watchlist data
    watchlist_data = data_handler.fetch_watchlist_data()
    
    # Get symbols currently in watchlist for this signal type
    watchlist_symbols = [
        item['symbol'] for item in watchlist_data
        if item['sheet'] == sheet_name and 
           item['supertrend'] == supertrend and 
           item['type'] == signal_type
    ]
    
    # Prepare display dataframe with watchlist checkbox column
    display_df = df[['Symbol', 'Close', 'LTP %', 'Pct Diff', 'Flatbase']].copy()
    
    # Add watchlist column - True if symbol is in watchlist
    display_df.insert(0, '📌', display_df['Symbol'].isin(watchlist_symbols))
    
    # Store original state for comparison
    original_state = display_df['📌'].copy()
    
    # Configure column types for data_editor
    column_config = {
        '📌': st.column_config.CheckboxColumn(
            '📌',
            help="Add/Remove from watchlist",
            default=False,
            width="small"
        ),
        'Symbol': st.column_config.TextColumn(
            'Symbol',
            width="medium"
        ),
        'Close': st.column_config.NumberColumn(
            'Close',
            format="%.2f",
            width="medium"
        ),
        'LTP %': st.column_config.NumberColumn(
            'LTP %',
            format="%.2f",
            width="medium"
        ),
        'Pct Diff': st.column_config.NumberColumn(
            'Pct Diff',
            format="%.2f",
            width="medium"
        ),
        'Flatbase': st.column_config.NumberColumn(
            'Flatbase',
            format="%d",
            width="medium"
        )
    }
    
    # Display editable dataframe with LARGE FONTS using CSS
    # Note: st.data_editor doesn't support pandas Styler, so we rely on CSS
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        disabled=['Symbol', 'Close', 'LTP %', 'Pct Diff', 'Flatbase'],
        key=f"{sheet_name}_{signal_type}_{supertrend}_df"
    )
    
    # Detect changes and update watchlist
    changes_made = False
    added_count = 0
    removed_count = 0
    
    for idx in range(len(edited_df)):
        original_checked = original_state.iloc[idx]
        current_checked = edited_df['📌'].iloc[idx]
        
        if original_checked != current_checked:
            symbol = edited_df['Symbol'].iloc[idx]
            pct = float(edited_df['Pct Diff'].iloc[idx])
            flatbase = int(edited_df['Flatbase'].iloc[idx])
            
            if current_checked and not original_checked:
                # Add to watchlist
                if watchlist_manager.add_to_watchlist(symbol, sheet_name, supertrend, signal_type, pct, flatbase):
                    added_count += 1
                    changes_made = True
            elif not current_checked and original_checked:
                # Remove from watchlist
                if watchlist_manager.remove_from_watchlist(symbol, sheet_name, supertrend, signal_type):
                    removed_count += 1
                    changes_made = True
    
    # Show status and trigger rerun if changes were made
    if changes_made:
        if added_count > 0:
            st.toast(f"✅ Added {added_count} symbol(s) to watchlist", icon="✅")
        if removed_count > 0:
            st.toast(f"❌ Removed {removed_count} symbol(s) from watchlist", icon="❌")
        data_handler.clear_watchlist_cache_only()
        st.rerun()
    
    # Show watchlist count
    st.caption(f"In watchlist: {len(watchlist_symbols)} symbols")


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
    
    # Apply pandas Styler for LARGE FONTS
    styled_watchlist = watchlist_df.style.set_properties(
        **{
            'font-size': '24pt',
            'text-align': 'center',
            'font-weight': '600',
            'padding': '12px'
        }
    ).set_table_styles([
        {
            'selector': 'th',
            'props': [
                ('font-size', '22pt'),
                ('text-align', 'center'),
                ('font-weight', '700'),
                ('padding', '12px')
            ]
        }
    ])
    
    # Display with row selection
    event = st.dataframe(
        styled_watchlist,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="watchlist_df"
    )
    
    selected_rows = event.selection.rows if event.selection else []
    
    # Remove button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption(f"Total: {len(watchlist_data)} | Selected: {len(selected_rows)}")
    with col2:
        if st.button("🗑️ Remove Selected", use_container_width=True):
            removed_count = 0
            for row_idx in selected_rows:
                if row_idx < len(watchlist_data):
                    item = watchlist_data[row_idx]
                    if watchlist_manager.remove_from_watchlist(
                        item['symbol'], item['sheet'], item['supertrend'], item['type']
                    ):
                        removed_count += 1
            
            if removed_count > 0:
                st.toast(f"❌ Removed {removed_count} item(s)", icon="❌")
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