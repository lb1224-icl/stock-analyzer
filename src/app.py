import dash
from dash import dcc, html, Output, Input, no_update
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from yahooquery import search

app = dash.Dash(__name__, suppress_callback_exceptions=True)
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
SEARCH_CACHE = {}


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
                # Left metrics
                html.Div([
                    html.H3("Key Metrics", style={"color": "white", "margin-bottom": "15px"}),
                    html.Div([
                        html.Div([html.Span("PE Ratio:", className="metric-label"), html.Span(id="pe-ratio", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Beta:", className="metric-label"), html.Span(id="beta", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Volume:", className="metric-label"), html.Span(id="volume", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Open:", className="metric-label"), html.Span(id="open", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Last Close:", className="metric-label"), html.Span(id="last-close", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Dividend Date:", className="metric-label"), html.Span(id="dividend-date", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Earnings Date:", className="metric-label"), html.Span(id="earnings-date", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("52-Week Range:", className="metric-label"), html.Span(id="week52-range", className="metric-value")], className="metric-row"),
                        html.Div([html.Span("Analysts Opinion:", className="metric-label"), html.Span(id="analyst-opinion", className="metric-value")], className="metric-row"),
                    ], className="metrics-container")
                ], className="overview-left card"),

                # Right graph
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



# Overview metrics
@app.callback(
    Output("pe-ratio", "children"),
    Output("beta", "children"),
    Output("volume", "children"),
    Output("open", "children"),
    Output("last-close", "children"),
    Output("dividend-date", "children"),
    Output("earnings-date", "children"),
    Output("week52-range", "children"),
    Output("analyst-opinion", "children"),
    Input("display-ticker-dropdown", "value")
)
def update_overview_metrics(ticker_symbol):
    if not ticker_symbol:
        return [""] * 9
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        pe = info.get("trailingPE", "N/A")
        beta = info.get("beta", "N/A")
        vol = info.get("volume", "N/A")
        o = info.get("open", "N/A")
        last = info.get("previousClose", "N/A")
        div_date = info.get("dividendDate", "N/A")
        earn_date = info.get("earningsDate", "N/A")
        week52 = f"{info.get('fiftyTwoWeekLow', 'N/A')} - {info.get('fiftyTwoWeekHigh', 'N/A')}"
        analyst = info.get("recommendationKey", "N/A")

        return [pe, beta, vol, o, last, div_date, earn_date, week52, analyst]
    except Exception:
        return ["N/A"] * 9

@app.callback(
    Output("overview-close-graph", "figure"),
    Input("display-ticker-dropdown", "value"),
    Input("overview-close-graph", "relayoutData")
)
def update_overview_graph(ticker_symbol, relayoutData):
    if not ticker_symbol:
        return go.Figure()

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(start="2020-01-01", end=pd.Timestamp.today())

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
            uirevision="overview"
        )
        return fig

    except Exception:
        return empty_fig("Overview", "Error fetching data")



# Main candlestick chart
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



# Candlestick creation
def create_candlestick(ticker_symbol, label_with_ticker, relayoutData, displayOptions):
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(start="2020-01-01", end=pd.Timestamp.today())
        if data.empty:
            return empty_fig(label_with_ticker, f"No data for {ticker_symbol}")

        for col in ["Open", "High", "Low", "Close"]:
            if col not in data.columns:
                return empty_fig(label_with_ticker, f"No {col} data for {ticker_symbol}")

        traces = [go.Candlestick(x=data.index, open=data["Open"], high=data["High"], low=data["Low"],
                                 close=data["Close"], name="Candlesticks")]

        if "MA50" in displayOptions:
            data["MA50"] = data["Close"].rolling(50).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA50"], mode="lines", line=dict(color="blue", width=1.5), name="MA50"))

        if "MA200" in displayOptions:
            data["MA200"] = data["Close"].rolling(200).mean()
            traces.append(go.Scatter(x=data.index, y=data["MA200"], mode="lines", line=dict(color="orange", width=1.5), name="MA200"))

        layout = go.Layout(
            template="plotly_dark",
            title=f"{label_with_ticker} Candlestick Chart",
            xaxis=dict(rangeslider=dict(visible=False), type="date"),
            margin=dict(l=20, r=20, t=50, b=40),
            uirevision="candles",
            showlegend=True
        )

        return go.Figure(data=traces, layout=layout)
    except Exception:
        return empty_fig(label_with_ticker, f"Error fetching data for {ticker_symbol}")



# Empty figure
def empty_fig(title, message):
    fig = go.Figure()
    fig.add_annotation(text=f"⚠️ {message}", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
                       font=dict(size=20, color="red"))
    fig.update_layout(title=f"{title} Candlestick Chart", template="plotly_dark")
    return fig

if __name__ == "__main__":
    app.run(debug=True)
