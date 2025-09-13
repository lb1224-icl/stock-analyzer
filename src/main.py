# main.py

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objs as go
import datetime

# -----------------------
# Sidebar controls
# -----------------------
st.sidebar.header("Stock Analyzer")
ticker = st.sidebar.text_input("Enter stock ticker", "AAPL")
start_date = st.sidebar.date_input("Start date", value=pd.to_datetime("2020-01-01"))
end_date = st.sidebar.date_input("End date", value=pd.to_datetime(datetime.date.today()))

# -----------------------
# Fetch data
# -----------------------
data = yf.download(ticker, start=start_date, end=end_date)

if data.empty:
    st.error("No data found for this ticker and date range.")
else:
    # -----------------------
    # Ensure 'Close' is a 1D Series
    # -----------------------
    if isinstance(data.columns, pd.MultiIndex):
        close_prices = data['Close'].iloc[:,0]  # pick first column if MultiIndex
    else:
        close_prices = data['Close']

    # -----------------------
    # Price Chart with Moving Averages
    # -----------------------
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'],
        low=data['Low'], close=close_prices,
        name='Price'
    )])

    ma50 = close_prices.rolling(50).mean()
    ma200 = close_prices.rolling(200).mean()

    fig.add_trace(go.Scatter(x=data.index, y=ma50, line=dict(color='blue'), name='MA 50'))
    fig.add_trace(go.Scatter(x=data.index, y=ma200, line=dict(color='orange'), name='MA 200'))

    st.title(f"📈 Stock Analyzer: {ticker}")
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------
    # Key Metrics
    # -----------------------
    daily_returns = close_prices.pct_change().dropna()

    cumulative_return = float(close_prices.iloc[-1] / close_prices.iloc[0] - 1)
    volatility = float(daily_returns.std() * (252 ** 0.5))
    sharpe_ratio = float((daily_returns.mean() / daily_returns.std()) * (252 ** 0.5))
    rolling_max = close_prices.cummax()
    drawdown = close_prices / rolling_max - 1
    max_drawdown = float(drawdown.min())

    st.subheader("📊 Key Metrics")
    st.metric("Cumulative Return", f"{cumulative_return:.2%}")
    st.metric("Annual Volatility", f"{volatility:.2%}")
    st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")
    st.metric("Max Drawdown", f"{max_drawdown:.2%}")
