import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from yahooquery import search
import time

last_search_time = 0

app = dash.Dash(__name__)

# Default popular tickers
default_options = [
    {"label": "Apple (AAPL)", "value": "AAPL"},
    {"label": "Microsoft (MSFT)", "value": "MSFT"},
    {"label": "Tesla (TSLA)", "value": "TSLA"},
    {"label": "NVIDIA (NVDA)", "value": "NVDA"},
    {"label": "Amazon (AMZN)", "value": "AMZN"},
    {"label": "Google (GOOGL)", "value": "GOOGL"},
    {"label": "Meta (META)", "value": "META"}
]

app.layout = html.Div([
    html.H1("📈 Smart Stock Candlestick Viewer", style={"color": "white"}),

    dcc.Dropdown(
        id="ticker-dropdown",
        options=default_options,
        value="AAPL",
        searchable=True,
        clearable=False,
        style={"width": "400px", "color": "black"}
    ),

    dcc.Graph(id="stock-chart")
], style={"backgroundColor": "black", "padding": "20px"})

# Update dropdown options on search

@app.callback(
    Output("ticker-dropdown", "options"),
    Input("ticker-dropdown", "search_value")
)
def update_dropdown_options(search_value):
    global last_search_time
    if not search_value:
        return default_options
    
    # Simple debounce: wait 0.5s after last call
    now = time.time()
    if now - last_search_time < 0.5:
        return dash.no_update
    last_search_time = now
    
    try:
        results = search(search_value)
        quotes = results.get("quotes", [])
        options = []
        for q in quotes[:10]:
            symbol = q.get("symbol")
            name = q.get("shortname") or q.get("longname") or symbol
            if symbol:
                options.append({"label": f"{name} ({symbol})", "value": symbol})
        return options if options else default_options
    except Exception as e:
        print(f"YahooQuery search error: {e}")
        return default_options



# Update chart with dynamic y-axis
@app.callback(
    Output("stock-chart", "figure"),
    Input("ticker-dropdown", "value"),
    Input("stock-chart", "relayoutData") 
)
def update_chart(ticker, relayoutData):
    if not ticker:
        return go.Figure()

    # Download stock data
    data = yf.download(ticker, start="2020-01-01", end=pd.Timestamp.today(), group_by="ticker")
    data = data.dropna()

    if data.empty:
        fig = go.Figure()
        fig.add_annotation(
            text=f"⚠️ No data for ticker '{ticker}'",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=20, color="red")
        )
        return fig

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[1] if col[1] else col[0] for col in data.columns]

    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="Candlesticks"
    )])

    if relayoutData and 'xaxis.range[0]' in relayoutData:
        start = pd.to_datetime(relayoutData['xaxis.range[0]'])
        end = pd.to_datetime(relayoutData['xaxis.range[1]'])
        visible_data = data.loc[start:end]

        if not visible_data.empty:
            y_min = max(visible_data['Low'].min() - 20, 0)
            y_max = visible_data['High'].max() + 20
            y_range = [y_min, y_max]
        else:
            y_range = [data['Low'].min(), data['High'].max()]
    else:
        y_range = [data['Low'].min(), data['High'].max()]

    fig.update_layout(
        template="plotly_dark",
        title=f"{ticker.upper()} Candlestick Chart",
        xaxis=dict(rangeslider=dict(visible=False), type="date"),
        yaxis=dict(range=y_range),
        uirevision=True,
        yaxis_title="Price ($)",
        xaxis_title="Date",
        margin=dict(l=20, r=20, t=50, b=40),
        dragmode="zoom"
    )

    return fig


# Run server
if __name__ == "__main__":
    app.run(debug=True)
