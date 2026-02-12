import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import requests

# --- 1. PERSISTENCE ENGINE ---
WATCHLIST_FILE = "watchlist_data.json"

def load_watchlist():
    """Loads saved tickers from a local JSON file."""
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_watchlist(watchlist):
    """Saves tickers to a local JSON file."""
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f)

# --- 2. DATA FETCH ENGINE (CACHED) ---
@st.cache_data(ttl=600)
def fetch_safe_data(ticker):
    """Fetches data using 'Human Headers' to prevent rate limits."""
    if not ticker: return None
    
    symbol = ticker if ticker.endswith(".SI") else ticker + ".SI"
    
    # Custom session to mimic a browser
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    try:
        stock = yf.Ticker(symbol, session=session)
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None
            
        return {
            "symbol": symbol,
            "name": info.get("longName", "Unknown"),
            "price": info.get("currentPrice", 0),
            "pe": info.get("trailingPE", 0),
            "div": info.get("dividendRate", 0),
            "bv": info.get("bookValue", 1),
            "roe": info.get("returnOnEquity", 0) * 100,
            "cash": info.get("totalCash", 0),
            "debt": info.get("totalDebt", 0),
        }
    except Exception:
        return None

# --- 3. MATH ENGINE ---
class SGXEngine:
    @staticmethod
    def calculate_fees(trade_value):
        """Standard SGX 2026 fee logic including 9% GST."""
        broker_comm = max(trade_value * 0.0003, 0.99)
        sgx_fees = trade_value * 0.0004
        settlement = 0.35
        return round((broker_comm + sgx_fees + settlement) * 1.09, 2)

# --- 4. APP INTERFACE ---
st.set_page_config(page_title="SGX Analyzer Pro", layout="wide")
st.title("🇸🇬 SGX Value Tracker 2026")
engine = SGXEngine()

# Initialize Watchlist from storage
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

tab1, tab2 = st.tabs(["🔍 Search & Add", "📊 Raw Watchlist"])

# --- TAB 1: SEARCH ---
with tab1:
    ticker_input = st.text_input("Enter SGX Ticker", placeholder="D05").upper().strip()
    if ticker_input:
        data = fetch_safe_data(ticker_input)
        if data:
            st.subheader(data['name'])
            c1, c2, c3 = st.columns(3)
            c1.metric("Current Price", f"S${data['price']:.2f}")
            c2.metric("Div Yield", f"{(data['div']/data['price'])*100:.2f}%")
            c3.metric("P/B Ratio", f"{data['price']/data['bv']:.2f}")
            
            if st.button("➕ Add to My Watchlist"):
                if not any(item['Ticker'] == data['symbol'] for item in st.session_state.watchlist):
                    st.session_state.watchlist.append({"Ticker": data['symbol'], "Name": data['name']})
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Added {data['name']}!")
                else:
                    st.warning("Already in list.")
        else:
            st.error("No data found. Ensure the ticker is correct.")

# --- TAB 2: WATCHLIST ---
with tab2:
    if st.session_state.watchlist:
        # Refresh logic
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        raw_rows = []
        with st.spinner("Updating Watchlist..."):
            for item in st.session_state.watchlist:
                d = fetch_safe_data(item['Ticker'])
                if d:
                    div_y = (d['div'] / d['price']) * 100 if d['price'] > 0 else 0
                    pb_v = d['price'] / d['bv']
                    net_c = d['cash'] - d['debt']
                    
                    raw_rows.append({
                        "Ticker": d['symbol'].replace(".SI", ""),
                        "Company": d['name'][:20], 
                        "Price": d['price'],
                        "P/E": d['pe'] if d['pe'] != 0 else "N/A",
                        "P/B": round(pb_v, 2),
                        "Yield %": round(div_y, 2),
                        "ROE %": round(d['roe'], 1),
                        "Net Cash (M)": round(net_c / 1_000_000, 1)
                    })
        
        if raw_rows:
            df = pd.DataFrame(raw_rows)
            
            # Interactive sorting
            sort_by = st.selectbox("Sort Watchlist By:", ["Yield %", "P/B", "ROE %", "Net Cash (M)"], index=0)
            df = df.sort_values(by=sort_by, ascending=(sort_by == "P/B")) # P/B sorts low-to-high

            # Conditional formatting function
            def style_fundamentals(val, column):
                if column == 'Yield %' and val >= 5: return 'background-color: #d1f2eb; color: #0e6251; font-weight: bold'
                if column == 'P/B' and val < 1.0: return 'background-color: #fdebd0; color: #935116; font-weight: bold'
                return ''

            # Show table
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Tip: Yield > 5% and P/B < 1.0 are generally considered value entries.")

        if st.button("🗑️ Clear Everything"):
            st.session_state.watchlist = []
            save_watchlist([])
            st.rerun()
    else:
        st.info("Your watchlist is empty. Go to the Search tab to add stocks.")

# --- 5. FOOTER ---
st.divider()
st.caption("SGX Analyzer 2026 | Built for Mobile | Data by Yahoo Finance")
