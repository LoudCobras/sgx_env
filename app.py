import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import requests
from datetime import datetime

# --- 1. PERSISTENCE ENGINE ---
WATCHLIST_FILE = "sgx_watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f)

# --- 2. RESILIENT DATA FETCH ---
@st.cache_data(ttl=600)
def fetch_safe_data(ticker):
    if not ticker: return None
    symbol = ticker if ticker.endswith(".SI") else ticker + ".SI"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })

    try:
        stock = yf.Ticker(symbol, session=session)
        # Layer 1: Full Info
        info = stock.info
        price = info.get("currentPrice") or info.get("regularMarketPrice")

        # Layer 2: Fast Info/History Fallback
        if price is None:
            hist = stock.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
        
        if price is None: return None

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "price": float(price),
            "pe": info.get("trailingPE", 0),
            "div": info.get("dividendRate", 0),
            "bv": info.get("bookValue", 1),
            "roe": info.get("returnOnEquity", 0) * 100,
            "cash": info.get("totalCash", 0),
            "debt": info.get("totalDebt", 0),
        }
    except: return None

# --- 3. UI CONFIG ---
st.set_page_config(page_title="SGX Tracker", layout="wide")
st.title("🇸🇬 SGX Value Tracker 2026")

# Sidebar for Debug & Admin
with st.sidebar:
    st.header("App Controls")
    if st.button("🔄 Hard Refresh (Clear Cache)"):
        st.cache_data.clear()
        st.rerun()
    if st.checkbox("Show Debug Logs"):
        st.write("Current Session State:", st.session_state.get('watchlist', []))

# Initialize Watchlist
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

tab1, tab2 = st.tabs(["🔍 Search", "📋 Watchlist (Raw)"])

# --- TAB 1: SEARCH ---
with tab1:
    search_q = st.text_input("Enter Ticker (e.g. D05, Z74)", value="").upper().strip()
    if search_q:
        data = fetch_safe_data(search_q)
        if data:
            st.subheader(data['name'])
            c1, c2, c3 = st.columns(3)
            c1.metric("Live Price", f"S${data['price']:.2f}")
            c2.metric("Yield", f"{(data['div']/data['price'])*100:.2f}%" if data['price'] > 0 else "0%")
            c3.metric("P/B Ratio", f"{data['price']/data['bv']:.2f}")
            
            if st.button("➕ Add to Watchlist"):
                if not any(item['Ticker'] == data['symbol'] for item in st.session_state.watchlist):
                    st.session_state.watchlist.append({"Ticker": data['symbol'], "Name": data['name']})
                    save_watchlist(st.session_state.watchlist)
                    st.success("Successfully Saved!")
        else:
            st.error("Data Fetch Failed. This is likely an IP limit from Yahoo Finance. Try the 'Hard Refresh' in the sidebar or check back in 10 mins.")

# --- TAB 2: WATCHLIST ---
with tab2:
    if st.session_state.watchlist:
        raw_rows = []
        progress_text = "Updating watchlist prices..."
        my_bar = st.progress(0, text=progress_text)
        
        for idx, item in enumerate(st.session_state.watchlist):
            d = fetch_safe_data(item['Ticker'])
            if d:
                div_y = (d['div'] / d['price']) * 100 if d['price'] > 0 else 0
                net_c = (d['cash'] - d['debt']) / 1_000_000 # In Millions
                
                raw_rows.append({
                    "Ticker": d['symbol'].replace(".SI", ""),
                    "Company": d['name'][:20],
                    "Price": d['price'],
                    "P/E": round(d['pe'], 1) if d['pe'] else "N/A",
                    "P/B": round(d['price'] / d['bv'], 2),
                    "Yield %": round(div_y, 2),
                    "ROE %": round(d['roe'], 1),
                    "Net Cash (M)": round(net_c, 1)
                })
            my_bar.progress((idx + 1) / len(st.session_state.watchlist), text=progress_text)
        my_bar.empty()

        if raw_rows:
            df = pd.DataFrame(raw_rows)
            
            # Interactive Sort
            sort_opt = st.selectbox("Sort By:", ["Yield %", "P/B", "Net Cash (M)", "ROE %"])
            df = df.sort_values(by=sort_opt, ascending=(sort_opt == "P/B"))

            # Conditional Formatting
            def apply_colors(val):
                color = ''
                if isinstance(val, (int, float)):
                    if 0 < val < 1.0: color = 'background-color: #d1f2eb; color: #0e6251;' # Green P/B
                    elif val > 5: color = 'background-color: #fdebd0; color: #935116;' # Orange Yield
                return color

            st.dataframe(df, use_container_width=True, hide_index=True)
            
        if st.button("🗑️ Clear My List"):
            st.session_state.watchlist = []
            save_watchlist([])
            st.rerun()
    else:
        st.info("No stocks saved yet. Search for a ticker to build your list.")

st.divider()
st.caption(f"Last sync: {datetime.now().strftime('%H:%M:%S')} | Data via Yahoo Finance")
