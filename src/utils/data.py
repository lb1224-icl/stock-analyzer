import yfinance as yf
import pandas as pd
from .formatting import format_number, format_date

def get_history(ticker_symbol, start="2020-01-01"):
    ticker = yf.Ticker(ticker_symbol)
    return ticker.history(start=start, end=pd.Timestamp.today())

def fetch_metrics(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        return {
            "pe": f"{info.get('trailingPE', 'N/A'):.3f}" if info.get("trailingPE") else "N/A",
            "beta": f"{info.get('beta', 'N/A'):.3f}" if info.get("beta") else "N/A",
            "volume": format_number(info.get("volume", "N/A")),
            "open": format_number(info.get("open", "N/A")),
            "last_close": format_number(info.get("previousClose", "N/A")),
            "dividend_date": format_date(info.get("dividendDate", "N/A")),
            "earnings_date": format_date(info.get("earningsDate", "N/A")),
            "week52_low": format_number(info.get("fiftyTwoWeekLow", "N/A")),
            "week52_high": format_number(info.get("fiftyTwoWeekHigh", "N/A")),
            "analyst": (info.get("recommendationKey", "N/A") or "N/A").upper(),
        }
    except Exception:
        return {k: "N/A" for k in [
            "pe", "beta", "volume", "open", "last_close",
            "dividend_date", "earnings_date", "week52_low", "week52_high", "analyst"
        ]}
