import streamlit as st
import yfinance as yf
import pandas as pd

# 1. FIXED: SAFE STANDALONE FETCH FUNCTION
@st.cache_data(ttl=600)  # Caches for 10 minutes
def fetch_safe_data(ticker):
    """Standalone function that won't crash on missing data."""
    if not ticker: return None
    
    symbol = ticker if ticker.endswith(".SI") else ticker + ".SI"
    try:
        stock = yf.Ticker(symbol)
        # Use .get() everywhere to provide '0' or 'N/A' if Yahoo is empty
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None
            
        return {
            "symbol": symbol,
            "name": info.get("longName", "Unknown"),
            "price": info.get("currentPrice", 0),
            "pe": info.get("trailingPE", "N/A"),
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

    def get_score(self, data):
        if not data: return 0
        score = 0
        pb = data['price'] / data['bv'] if data['bv'] != 0 else 10
        div_yield = (data['div'] / data['price']) * 100 if data['price'] > 0 else 0
        
        if isinstance(data.get("pe"), (int, float)) and data["pe"] < 15: score += 2
        if pb < 1.0: score += 2
        if div_yield > 4.5: score += 2
        if data.get("roe", 0) > 10: score += 2
        if (data['cash'] - data['debt']) > 0: score += 2
        return score

# --- APP UI ---
st.set_page_config(page_title="SGX Analyzer", layout="centered")
st.title("🇸🇬 SGX Value Analyzer")
engine = SGXEngine()

# Initialize session state for Watchlist
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["D05", "Z74"]

tab1, tab2 = st.tabs(["🔍 Search", "📋 Watchlist"])

with tab1:
    ticker_input = st.text_input("Enter Ticker", value="D05").upper().strip()
    if st.button("Run Analysis"):
        data = fetch_safe_data(ticker_input)
        if data:
            score = engine.get_score(data)
            st.metric(label=data['name'], value=f"S${data['price']:.2f}", delta=f"Score: {score}/10")
            
            # Show Metrics
            c1, c2 = st.columns(2)
            c1.write(f"**P/E:** {data['pe']}")
            c2.write(f"**Yield:** {(data['div']/data['price'])*100:.1f}%")
            
            if st.button("➕ Add to Watchlist"):
                if ticker_input not in st.session_state.watchlist:
                    st.session_state.watchlist.append(ticker_input)
                    st.success(f"Added {ticker_input}!")
        else:
            st.error("Data fetch failed. Ticker might be wrong or Yahoo is busy.")

with tab2:
    st.subheader("Saved Stocks")
    if st.session_state.watchlist:
        rows = []
        for t in st.session_state.watchlist:
            d = fetch_safe_data(t)  # Now using the safe standalone function
            if d:  # FIXED: Only add to table if data actually exists!
                s = engine.get_score(d)
                rows.append({"Ticker": t, "Price": f"S${d['price']:.2f}", "Score": f"{s}/10"})
        
        if rows:
            st.table(pd.DataFrame(rows))
        else:
            st.warning("Could not load data for stocks in your list.")
        
        if st.button("🗑️ Clear Watchlist"):
            st.session_state.watchlist = []
            st.rerun()
