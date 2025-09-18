from datetime import datetime
import pandas as pd

def format_number(value):
    try:
        num = float(value)
        if num >= 1e9: return f"{num/1e9:.2f}B"
        if num >= 1e6: return f"{num/1e6:.2f}M"
        if num >= 1e3: return f"{num/1e3:.2f}K"
        return f"{num:.2f}"
    except Exception:
        return value

def format_date(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.utcfromtimestamp(value).strftime("%d/%m/%Y")
        elif isinstance(value, str):
            return pd.to_datetime(value).strftime("%d/%m/%Y")
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return "N/A"
