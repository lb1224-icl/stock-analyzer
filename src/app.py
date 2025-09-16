import dash
from dash import dcc, html, Output, Input
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from yahooquery import search

app = dash.Dash(__name__)
app.title = "Stock Tracker"

DEFAULT_STOCKS = [
    {"label": "Apple", "value": "AAPL"},
    {"label": "Microsoft", "value": "MSFT"},
    {"label": "Tesla", "value": "TSLA"},
    {"label": "Amazon", "value": "AMZN"},
    {"label": "Nvidia", "value": "NVDA"},
    {"label": "Google", "value": "GOOGL"},
    {"label": "Meta", "value": "META"},
    {"label": "Netflix", "value": "NFLX"},
    {"label": "Berkshire Hathaway", "value": "BRK-B"},
    {"label": "JPMorgan Chase", "value": "JPM"},
]

DEFAULT_LABEL_LOOKUP = {s["value"]: s["label"] for s in DEFAULT_STOCKS}
SEARCH_CACHE = {}  # ticker -> label

app.layout = html.Div([

    # Main title
    html.H1("Stock Tracker", className="app-title"),

    # Control panel (wrapped in box)
    html.Div([
        html.Div([
            html.Label("Ticker", className="section-label"),
            dcc.Dropdown(
                id="display-ticker-dropdown",
                options=[{"label": f"{s['label']} ({s['value']})", "value": s["value"]} for s in DEFAULT_STOCKS],
                value="AAPL",
                placeholder="Search for a stock...",
                clearable=False,
                searchable=True,
                className="dropdown"
            )
        ], className="control"),

        html.Div([
            html.Label("Display Options", className="section-label"),
            dcc.Checklist(
                id="display-options",
                options=[
                    {"label": "MA50", "value": "MA50"},
                    {"label": "MA200", "value": "MA200"}
                ],
                value=[],
                className="checklist"
            )
        ], className="control")
    ], className="control-panel"),

    # Graph
    html.Div([
        dcc.Graph(id="stock-chart", className="stock-graph")
    ], className="graph-container")

], className="app-container")




# Dropdown options update
@app.callback(
    Output("display-ticker-dropdown", "options"),
    Input("display-ticker-dropdown", "search_value"),
    Input("display-ticker-dropdown", "value")
)
def update_options(search_value, selected_value):
    # Prepare search options first
    search_options = []
    if search_value:
        results = search(search_value, first_quote=False, quotes_count=10).get("quotes", [])[:10]
        for q in results:
            sym = q.get("symbol")
            if not sym:
                continue
            label = q.get("shortname") or q.get("shortName") or sym
            SEARCH_CACHE[sym] = label
            search_options.append({"label": f"{label} ({sym})", "value": sym})

    # Add defaults at the bottom
    default_options = []
    existing_values = [opt["value"] for opt in search_options]
    for s in DEFAULT_STOCKS:
        if s["value"] not in existing_values:
            default_options.append({"label": f"{s['label']} ({s['value']})", "value": s["value"]})

    if selected_value and selected_value not in [opt["value"] for opt in search_options + default_options]:
        label = SEARCH_CACHE.get(selected_value, selected_value)
        search_options.append({"label": f"{label} ({selected_value})", "value": selected_value})

    return search_options + default_options


# Candlestick update
@app.callback(
    Output("stock-chart", "figure"),
    Input("display-ticker-dropdown", "value"),
    Input("stock-chart", "relayoutData"),
    Input("display-options", "value")
)
def update_chart(ticker, relayoutData, displayOptions):
    if not ticker:
        return go.Figure()

    label = DEFAULT_LABEL_LOOKUP.get(ticker) or SEARCH_CACHE.get(ticker) or ticker
    label_with_ticker = f"{label} ({ticker})"

    return create_candlestick(ticker, label_with_ticker, relayoutData, displayOptions)

# Candlestick helpers
def create_candlestick(ticker, label_with_ticker, relayoutData, displayOptions):
    data = yf.download(ticker, start="2020-01-01", end=pd.Timestamp.today(), group_by="ticker")

    if data.empty:
        return empty_fig(label_with_ticker, f"No data for {ticker}")

    if isinstance(data.columns, pd.MultiIndex):
        data = collapse_data(data)

    # Ensure OHLC columns exist
    for col in ['Open', 'High', 'Low', 'Close']:
        if col not in data.columns:
            return empty_fig(label_with_ticker, f"No {col} data for {ticker}")

    candlestick = go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name="Candlesticks"
    )

    traces = [candlestick]

    # Add MA50 if selected
    if "MA50" in displayOptions:
        data["MA50"] = data["Close"].rolling(window=50).mean()
        traces.append(
            go.Scatter(
                x=data.index,
                y=data["MA50"],
                mode="lines",
                line=dict(color="blue", width=1.5),
                name="MA50"
            )
        )

    # Add MA200 if selected
    if "MA200" in displayOptions:
        data["MA200"] = data["Close"].rolling(window=200).mean()
        traces.append(
            go.Scatter(
                x=data.index,
                y=data["MA200"],
                mode="lines",
                line=dict(color="orange", width=1.5),
                name="MA200"
            )
        )

    layout = go.Layout(
        template="plotly_dark",
        title=f"{label_with_ticker} Candlestick Chart",
        xaxis=dict(rangeslider=dict(visible=False), type="date"),
        yaxis=dict(range=handle_yrange(data, relayoutData)),
        uirevision=True,
        yaxis_title="Price ($)",
        xaxis_title="Date",
        margin=dict(l=20, r=20, t=50, b=40),
        showlegend=True,
    )

    fig = go.Figure(data=traces, layout=layout)

    return fig

def collapse_data(data):
    data.columns = [col[1] if isinstance(col, tuple) and col[1] else col[0] for col in data.columns]
    return data

def empty_fig(title, message):
    fig = go.Figure()
    fig.add_annotation(
        text=f"⚠️ {message}",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=20, color="red")
    )
    fig.update_layout(title=f"{title} Candlestick Chart", template="plotly_dark")
    return fig

def handle_yrange(data, relayoutData):
    if relayoutData and 'xaxis.range[0]' in relayoutData:
        start = pd.to_datetime(relayoutData['xaxis.range[0]'])
        end = pd.to_datetime(relayoutData['xaxis.range[1]'])
        visible_data = data.loc[start:end]
        if not visible_data.empty:
            y_min = max(visible_data['Low'].min(), 0)
            y_max = visible_data['High'].max()
            y_range = [y_min, y_max]
        else:
            y_range = [data['Low'].min(), data['High'].max()]
    else:
        y_range = [data['Low'].min(), data['High'].max()]

    y_range_int = y_range[1] - y_range[0]
    y_range[0] -= y_range_int / 10
    y_range[1] += y_range_int / 10
    return y_range

if __name__ == "__main__":
    app.run(debug=True)
