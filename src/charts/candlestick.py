import plotly.graph_objs as go
from utils.data import get_history
from utils.figures import empty_fig, handle_yrange

def create_candlestick(ticker_symbol, label_with_ticker, relayoutData, displayOptions):
    try:
        data = get_history(ticker_symbol)
        if data.empty:
            return empty_fig(label_with_ticker, f"No data for {ticker_symbol}")

        for col in ["Open", "High", "Low", "Close"]:
            if col not in data.columns:
                return empty_fig(label_with_ticker, f"No {col} data")

        traces = [go.Candlestick(
            x=data.index, open=data["Open"], high=data["High"],
            low=data["Low"], close=data["Close"], name="Candlesticks"
        )]

        if "MA50" in displayOptions:
            data["MA50"] = data["Close"].rolling(50).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA50"], mode="lines",
                                     line=dict(color="blue", width=1.5), name="MA50"))
        if "MA200" in displayOptions:
            data["MA200"] = data["Close"].rolling(200).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA200"], mode="lines",
                                     line=dict(color="orange", width=1.5), name="MA200"))

        return go.Figure(
            data=traces,
            layout=go.Layout(
                template="plotly_dark",
                title=f"{label_with_ticker} Candlestick Chart",
                xaxis=dict(type="date", rangeslider=dict(visible=False)),
                yaxis=dict(range=handle_yrange(data, relayoutData)),
                margin=dict(l=20, r=20, t=50, b=40),
                uirevision="candles",
                showlegend=True,
            )
        )
    except Exception:
        return empty_fig(label_with_ticker, f"Error fetching {ticker_symbol}")
