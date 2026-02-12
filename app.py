import streamlit as st
import yfinance as yf
import pandas as pd

# Add this above your fetch_stock_data function
@st.cache_data(ttl=300) # This remembers data for 300 seconds (5 mins)
def fetch_stock_data(self, ticker):
    symbol = ticker if ticker.endswith(".SI") else ticker + ".SI"
    stock = yf.Ticker(symbol)
    # ... rest of your code ...
    info = stock.info
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


# --- CORE ENGINE LOGIC ---
class SGXEngine:
    @staticmethod
    def calculate_fees(trade_value):
        broker_comm = max(trade_value * 0.0003, 0.99)
        sgx_fees = trade_value * 0.0004
        settlement = 0.35
        return round((broker_comm + sgx_fees + settlement) * 1.09, 2)

    @staticmethod
    def get_score(data):
        score = 0
        pb = data["price"] / data["bv"] if data["bv"] != 0 else 10
        div_yield = (data["div"] / data["price"]) * 100 if data["price"] > 0 else 0
        net_cash = data["cash"] - data["debt"]

        if isinstance(data.get("pe"), (int, float)) and data["pe"] < 15:
            score += 2
        if pb < 1.0:
            score += 2
        if div_yield > 4.5:
            score += 2
        if data.get("roe", 0) > 10:
            score += 2
        if net_cash > 0:
            score += 2
        return score

# --- STREAMLIT UI ---
st.set_page_config(page_title="SGX Analyzer", layout="centered")
engine = SGXEngine()

# Initialize Watchlist in session memory
if "watchlist" not in st.session_state:
    st.session_state.watchlist = ["D05", "Z74", "U11"]  # Default starters

st.title("🇸🇬 SGX Value App")

tab1, tab2 = st.tabs(["🔍 Search", "📋 Watchlist"])

with tab1:
    ticker = st.text_input("Enter SGX Ticker", placeholder="e.g. D05").upper()
    if st.button("Analyze"):
        with st.spinner("Fetching 2026 Data..."):
            data = engine.fetch_stock_data(ticker)
            if data["price"] > 0:
                score = engine.get_score(data)

                # Mobile Metric Cards
                c1, c2 = st.columns(2)
                c1.metric("Price", f"S${data['price']:.2f}")
                c2.metric("Value Score", f"{score}/10")

                st.progress(score / 10)

                # Expandable Details
                with st.expander("Financial Details"):
                    st.write(f"**P/E:** {data['pe']}")
                    st.write(f"**ROE:** {data['roe']:.1f}%")
                    st.write(f"**Net Cash:** S${(data['cash']-data['debt']):,.0f}")

                if st.button("Add to Watchlist"):
                    if ticker not in st.session_state.watchlist:
                        st.session_state.watchlist.append(ticker)
                        st.success(f"Added {ticker}!")
            else:
                st.error("Ticker not found.")

with tab2:
    st.subheader("Your Watchlist")
    if st.session_state.watchlist:
        watchlist_data = []
        for t in st.session_state.watchlist:
            d = engine.fetch_stock_data(t)
            score = engine.get_score(d)
            watchlist_data.append(
                {"Ticker": t, "Price": d["price"], "Score": f"{score}/10"}
            )

        st.table(pd.DataFrame(watchlist_data))
        if st.button("Clear Watchlist"):
            st.session_state.watchlist = []
            st.rerun()
    else:
        st.write("Watchlist is empty.")



