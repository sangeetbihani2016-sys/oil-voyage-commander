import streamlit as st
import yfinance as yf


@st.cache_data(ttl=300)
def fetch_live_crude_prices():
    """Fetch Brent and WTI front-month futures using Yahoo fast_info."""
    fallback_prices = {"brent": 80.00, "wti": 75.00}

    try:
        brent = yf.Ticker("BZ=F").fast_info["last_price"]
        wti = yf.Ticker("CL=F").fast_info["last_price"]

        return {
            "brent": round(float(brent), 2),
            "wti": round(float(wti), 2),
        }
    except Exception as exc:
        st.warning(
            "Yahoo Finance is temporarily unreachable. "
            f"Using fallback crude prices for P&L calculations. Details: {exc}"
        )
        return fallback_prices
