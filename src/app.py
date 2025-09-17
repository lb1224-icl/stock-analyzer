import dash
from dash import dcc, html, Output, Input, no_update
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from yahooquery import search
import math
from datetime import datetime


app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Stock Tracker"

# Default stocks
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
SEARCH_CACHE = {}


# Utility: fetch ticker history
def get_history(ticker_symbol, start="2020-01-01"):
    ticker = yf.Ticker(ticker_symbol)
    return ticker.history(start=start, end=pd.Timestamp.today())


# Utility: fetch key metrics
def fetch_metrics(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        metrics = {
            "pe": f"{info.get("trailingPE", "N/A"):.3f}",
            "beta": f"{info.get("beta", "N/A"):.3f}",
            "volume": format_number(info.get("volume", "N/A")),
            "open": format_number(info.get("open", "N/A")),
            "last_close": format_number(info.get("previousClose", "N/A")),
            "dividend_date": format_date(info.get("dividendDate", "N/A")),
            "earnings_date": format_date(info.get("earningsDate", "N/A")),
            "week52_low": format_number(info.get('fiftyTwoWeekLow', 'N/A')),
            "week52_high": format_number(info.get('fiftyTwoWeekHigh', 'N/A')),
            "analyst": info.get("recommendationKey", "N/A").upper(),
        }
        return metrics
    except Exception:
        return {k: "N/A" for k in [
            "pe", "beta", "volume", "open", "last_close",
            "dividend_date", "earnings_date", "week52_range", "analyst"
        ]}



# Utility: empty/error figure
def empty_fig(title, message, chart_type="Chart"):
    fig = go.Figure()
    fig.add_annotation(
        text=f"⚠️ {message}",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=20, color="red")
    )
    fig.update_layout(title=f"{title} {chart_type}", template="plotly_dark")
    return fig

# Utility: y-axis range handler for zoom
def handle_yrange(data, relayoutData):
    low_col = "Low" if "Low" in data.columns else "Close"
    high_col = "High" if "High" in data.columns else "Close"

    if relayoutData and "xaxis.range[0]" in relayoutData and "xaxis.range[1]" in relayoutData:
        start = pd.to_datetime(relayoutData["xaxis.range[0]"])
        end = pd.to_datetime(relayoutData["xaxis.range[1]"])
        
        # Align timezone with data.index
        if data.index.tz is not None:
            start = start.tz_localize(data.index.tz)
            end = end.tz_localize(data.index.tz)
        
        visible_data = data.loc[start:end]
        if not visible_data.empty:
            y_min = max(visible_data[low_col].min(), 0)
            y_max = visible_data[high_col].max()
        else:
            y_min, y_max = data[low_col].min(), data[high_col].max()
    else:
        y_min, y_max = data[low_col].min(), data[high_col].max()

    y_range_int = y_max - y_min if y_max != y_min else y_max * 0.05
    return [y_min - y_range_int * 0.05, y_max + y_range_int * 0.05]


# Utility: formats numbers into conpact form
def format_number(value):
    try:
        num = float(value)
        if num >= 1e9:
            return f"{num/1e9:.2f}B"
        elif num >= 1e6:
            return f"{num/1e6:.2f}M"
        elif num >= 1e3:
            return f"{num/1e3:.2f}K"
        else:
            return f"{num:.2f}"
    except Exception:
        return value
    
# Utility: formats dates correctly
def format_date(value):
    try:
        if isinstance(value, (int, float)):  # Unix timestamp
            return datetime.utcfromtimestamp(value).strftime("%d/%m/%Y")
        elif isinstance(value, str):  # Sometimes already a string
            return pd.to_datetime(value).strftime("%d/%m/%Y")
        return pd.to_datetime(value).strftime("%d/%m/%Y")
    except Exception:
        return "N/A"

# Layout
app.layout = html.Div([
    html.H1("Stock Tracker", className="app-title"),

    html.Div([
        html.Div([
            dcc.Dropdown(
                id="display-ticker-dropdown",
                options=[{"label": f"{s['label']} ({s['value']})", "value": s["value"]} for s in DEFAULT_STOCKS],
                value="AAPL",
                placeholder="Search for a stock...",
                clearable=False,
                searchable=True,
                className="dropdown"
            )
        ], className="top-left"),

        html.Div([
            dcc.Tabs(
                id="page-tabs",
                value="charts",
                children=[
                    dcc.Tab(label="Overview", value="overview", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="Charts", value="charts", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="Dividends", value="dividends", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="History", value="history", className="tab", selected_className="tab--selected")
                ],
                className="tabs"
            )
        ], className="top-right")
    ], className="top-card"),

    html.Div(id="page-content")
], className="app-container")


# Dropdown search update
@app.callback(
    Output("display-ticker-dropdown", "options"),
    Input("display-ticker-dropdown", "search_value"),
    Input("display-ticker-dropdown", "value")
)
def update_options(search_value, selected_value):
    search_options = []
    if search_value:
        try:
            results = search(search_value, first_quote=False, quotes_count=10).get("quotes", [])[:10]
            for q in results:
                sym = q.get("symbol")
                if not sym:
                    continue
                label = q.get("shortname") or q.get("shortName") or sym
                SEARCH_CACHE[sym] = label
                search_options.append({"label": f"{label} ({sym})", "value": sym})
        except Exception:
            pass

    default_options = []
    existing_values = [opt["value"] for opt in search_options]
    for s in DEFAULT_STOCKS:
        if s["value"] not in existing_values:
            default_options.append({"label": f"{s['label']} ({s['value']})", "value": s["value"]})

    if selected_value and selected_value not in [opt["value"] for opt in search_options + default_options]:
        label = SEARCH_CACHE.get(selected_value, selected_value)
        search_options.append({"label": f"{label} ({selected_value})", "value": selected_value})

    return search_options + default_options


# Page content switch
@app.callback(
    Output("page-content", "children"),
    Input("page-tabs", "value"),
    Input("display-ticker-dropdown", "value")
)
def render_tab(tab, ticker):
    if tab == "overview":
        return html.Div([
            html.Div([
                html.Div([
                    html.H3("Key Metrics", style={"color": "white", "margin-bottom": "15px"}),

                    html.Div([
                        # Left column
                        html.Div([
                            html.Div([html.Span("PE Ratio", className="metric-label"), html.Span(id="pe-ratio", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Beta", className="metric-label"), html.Span(id="beta", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("52-Week Low", className="metric-label"), html.Span(id="week52-low", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Volume", className="metric-label"), html.Span(id="volume", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Open", className="metric-label"), html.Span(id="open", className="metric-value")], className="metric-card"),
                            
                        ], className="metrics-col"),

                        # Right column
                        html.Div([
                            html.Div([html.Span("Dividend Date", className="metric-label"), html.Span(id="dividend-date", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Earnings Date", className="metric-label"), html.Span(id="earnings-date", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("52-Week High", className="metric-label"), html.Span(id="week52-high", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Analysts Opinion", className="metric-label"), html.Span(id="analyst-opinion", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Last Close", className="metric-label"), html.Span(id="last-close", className="metric-value")], className="metric-card"),
                        ], className="metrics-col"),

                    ], className="metrics-grid")
                ], className="overview-left card"),

                html.Div([
                    html.H3("Close Price History", style={"color": "white", "margin-bottom": "15px"}),
                    dcc.Loading(
                        id="loading-overview-graph",
                        type="circle",
                        children=dcc.Graph(id="overview-close-graph", className="overview-graph")
                    )
                ], className="overview-right card"),

            ], className="overview-container")
        ])
    elif tab == "dividends":
        return html.Div([html.Div([html.H3("Dividends coming soon...", style={"color": "white", "margin": "10px"})], className="card")])
    elif tab == "history":
        return html.Div([html.Div([html.H3("History coming soon...", style={"color": "white", "margin": "10px"})], className="card")])
    elif tab == "charts":
        return html.Div([
            html.Div([
                html.Label("Display Options:", className="section-label"),
                dcc.Checklist(
                    id="display-options",
                    options=[{"label": "MA50", "value": "MA50"}, {"label": "MA200", "value": "MA200"}],
                    value=[],
                    className="checklist"
                )
            ], className="card"),
            html.Div([
                dcc.Loading(
                    id="loading-stock-chart",
                    type="circle",
                    children=dcc.Graph(id="stock-chart", className="stock-graph")
                )
            ], className="card")
        ])
    return html.Div()


# Update overview metrics
@app.callback(
    Output("pe-ratio", "children"),
    Output("beta", "children"),
    Output("volume", "children"),
    Output("open", "children"),
    Output("last-close", "children"),
    Output("dividend-date", "children"),
    Output("earnings-date", "children"),
    Output("week52-low", "children"),
    Output("week52-high", "children"),
    Output("analyst-opinion", "children"),
    Input("display-ticker-dropdown", "value")
)
def update_overview_metrics(ticker_symbol):
    if not ticker_symbol:
        return [""] * 9
    try:
        metrics = fetch_metrics(ticker_symbol)
        return [
            metrics["pe"], metrics["beta"], metrics["volume"], metrics["open"],
            metrics["last_close"], metrics["dividend_date"], metrics["earnings_date"],
            metrics["week52_low"], metrics["week52_high"], metrics["analyst"]
        ]
    except Exception:
        return ["N/A"] * 9


# Update overview graph
@app.callback(
    Output("overview-close-graph", "figure"),
    Input("display-ticker-dropdown", "value"),
    Input("overview-close-graph", "relayoutData")
)
def update_overview_graph(ticker_symbol, relayoutData):
    if not ticker_symbol:
        return go.Figure()
    try:
        hist = get_history(ticker_symbol)
        if hist.empty:
            return empty_fig("Overview", "No data")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index,
            y=hist["Close"],
            fill="tozeroy",
            line=dict(color="cyan", width=2),
            name="Close"
        ))

        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(type="date"),
            yaxis=dict(range=handle_yrange(hist, relayoutData)),
            uirevision="overview"
        )
        return fig
    except Exception:
        return empty_fig("Overview", "Error fetching data")


# Candlestick chart
@app.callback(
    Output("stock-chart", "figure"),
    Input("display-ticker-dropdown", "value"),
    Input("display-options", "value"),
    Input("stock-chart", "relayoutData"),
)
def update_chart(ticker_symbol, displayOptions, relayoutData):
    if not ticker_symbol:
        return no_update

    label = DEFAULT_LABEL_LOOKUP.get(ticker_symbol) or SEARCH_CACHE.get(ticker_symbol) or ticker_symbol
    label_with_ticker = f"{label} ({ticker_symbol})"
    return create_candlestick(ticker_symbol, label_with_ticker, relayoutData, displayOptions)


def create_candlestick(ticker_symbol, label_with_ticker, relayoutData, displayOptions):
    try:
        data = get_history(ticker_symbol)
        if data.empty:
            return empty_fig(label_with_ticker, f"No data for {ticker_symbol}")

        for col in ["Open", "High", "Low", "Close"]:
            if col not in data.columns:
                return empty_fig(label_with_ticker, f"No {col} data for {ticker_symbol}")

        traces = [go.Candlestick(
            x=data.index, open=data["Open"], high=data["High"],
            low=data["Low"], close=data["Close"], name="Candlesticks"
        )]

        if "MA50" in displayOptions:
            data["MA50"] = data["Close"].rolling(50).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA50"], mode="lines", line=dict(color="blue", width=1.5), name="MA50"))
        if "MA200" in displayOptions:
            data["MA200"] = data["Close"].rolling(200).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA200"], mode="lines", line=dict(color="orange", width=1.5), name="MA200"))

        layout = go.Layout(
            template="plotly_dark",
            title=f"{label_with_ticker} Candlestick Chart",
            xaxis=dict(type="date", rangeslider=dict(visible=False)),  # no scrollbar
            yaxis=dict(range=handle_yrange(data, relayoutData)),
            margin=dict(l=20, r=20, t=50, b=40),
            uirevision="candles",
            showlegend=True
        )

        return go.Figure(data=traces, layout=layout)
    except Exception:
        return empty_fig(label_with_ticker, f"Error fetching data for {ticker_symbol}")


if __name__ == "__main__":
    app.run(debug=True)
