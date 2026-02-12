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
    st.session_state.watchlist = [
        {"Ticker":"D05.SI","Name":"DBS Group Holdings Ltd 星展银行"}, 
        {"Ticker":"Z74.SI","Name":"Singtel 新电信"},
        {"Ticker":"U11.SI","Name":"United Overseas Bank (UOB) 大华银行"}
    ]

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
            # Check if ticker already exists in our list of dictionaries
            exists = any(item['Ticker'] == data['symbol'] for item in st.session_state.watchlist)
        if not exists:
            st.session_state.watchlist.append({
                "Ticker": data['symbol'], 
                "Name": data['name']
            })
            st.success(f"Added {data['name']} to your list!")
        else:
            st.warning("This stock is already in your watchlist.")
    else:
        st.error("Data fetch failed. Ticker might be wrong or Yahoo is busy.")

with tab2:
    st.subheader("Your Portfolio Watchlist")
    
    if st.session_state.watchlist:
        watchlist_display = []
        
        for item in st.session_state.watchlist:
            # Re-fetch live data for the price/score refresh
            d = fetch_safe_data(item['Ticker'])
            if d:
                score = engine.get_score(d)
                watchlist_display.append({
                    "Ticker": item['Ticker'],
                    "Company Name": item['Name'],  # Now using the saved name
                    "Price": f"S${d['price']:.2f}",
                    "Score": f"{score}/10"
                })
        
        if watchlist_display:
            # Convert to DataFrame for a clean table
            df = pd.DataFrame(watchlist_display)
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ Clear All"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.info("Your watchlist is empty. Add stocks from the Search tab!")

