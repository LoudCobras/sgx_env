import streamlit as st
import yfinance as yf
import pandas as pd

# 1. SAFE STANDALONE FETCH FUNCTION
@st.cache_data(ttl=600)
def fetch_safe_data(ticker):
    if not ticker: return None
    symbol = ticker if ticker.endswith(".SI") else ticker + ".SI"
    
    import requests
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

class SGXEngine:
    @staticmethod
    def calculate_fees(trade_value):
        broker_comm = max(trade_value * 0.0003, 0.99)
        sgx_fees = trade_value * 0.0004
        settlement = 0.35
        return round((broker_comm + sgx_fees + settlement) * 1.09, 2)

# --- APP UI ---
st.set_page_config(page_title="SGX Raw Analyzer", layout="wide") # 'Wide' is better for tables
st.title("🇸🇬 SGX Fundamentals Tracker")
engine = SGXEngine()

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = [
        {"Ticker": "D05.SI", "Name": "DBS Group"},
        {"Ticker": "Z74.SI", "Name": "Singtel"}
    ]

tab1, tab2 = st.tabs(["🔍 Search", "📋 Raw Watchlist"])

with tab1:
    ticker_input = st.text_input("Enter Ticker", value="").upper().strip()
    if st.button("Analyze"):
        data = fetch_safe_data(ticker_input)
        if data:
            st.subheader(data['name'])
            col1, col2, col3 = st.columns(3)
            col1.metric("Price", f"S${data['price']:.2f}")
            col2.metric("Yield", f"{(data['div']/data['price'])*100:.2f}%")
            col3.metric("P/B Ratio", f"{data['price']/data['bv']:.2f}")
            
            if st.button("➕ Add to Watchlist"):
                if not any(item['Ticker'] == data['symbol'] for item in st.session_state.watchlist):
                    st.session_state.watchlist.append({"Ticker": data['symbol'], "Name": data['name']})
                    st.success("Added!")
        else:
            st.error("Could not fetch data.")

with tab2:
    if st.session_state.watchlist:
        raw_rows = []
        for item in st.session_state.watchlist:
            d = fetch_safe_data(item['Ticker'])
            if d:
                div_y = (d['div'] / d['price']) * 100 if d['price'] > 0 else 0
                pb_v = d['price'] / d['bv']
                net_c = d['cash'] - d['debt']
                
                raw_rows.append({
                    "Ticker": d['symbol'].replace(".SI", ""),
                    "Company": d['name'][:15], 
                    "Price": d['price'],
                    "P/E": d['pe'] if d['pe'] != 0 else "N/A",
                    "P/B": round(pb_v, 2),
                    "Yield %": round(div_y, 2),
                    "ROE %": round(d['roe'], 1),
                    "Net Cash (M)": round(net_c / 1_000_000, 1)
                })
        
        if raw_rows:
            df = pd.DataFrame(raw_rows)

            # --- ADDED: SORTING FEATURE ---
            sort_col = st.selectbox("Sort by:", ["Yield %", "P/B", "Price", "ROE %"], index=0)
            df = df.sort_values(by=sort_col, ascending=False if "Yield" in sort_col else True)

            # --- FIXED: SAFE STYLING ---
            def color_values(val):
                if isinstance(val, (int, float)):
                    if 5 <= val <= 100: return 'color: #2ecc71; font-weight: bold'
                    if 0 < val < 1.0: return 'color: #2ecc71; font-weight: bold'
                return ''

            # We check if columns exist before applying style to prevent KeyError
            target_cols = [col for col in ['P/B', 'Yield %'] if col in df.columns]
            
            if target_cols:
                st.dataframe(df.style.applymap(color_values, subset=target_cols), 
                             use_container_width=True, hide_index=True)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Clear List"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.info("Watchlist is empty.")
