import dash
from dash import dcc, html, Output, Input, State, ALL, no_update
import plotly.graph_objs as go

# Local imports
from utils.data import fetch_metrics, get_history
from utils.figures import empty_fig, handle_yrange
from charts.candlestick import create_candlestick
from components.stock_dropdown import StockDropdown, SEARCH_CACHE, DEFAULT_STOCKS

from yahooquery import search

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Stock Tracker"

# Lookup dictionary for defaults
DEFAULT_LABEL_LOOKUP = {s["value"]: s["label"] for s in DEFAULT_STOCKS}

# Main dropdown
main_dropdown = StockDropdown(app, component_id="display-ticker-dropdown")

# Layout
app.layout = html.Div([
    html.H1("Stock Tracker", className="app-title"),

    html.Div([
        html.Div([main_dropdown.render()], className="top-left"),

        html.Div([
            dcc.Tabs(
                id="page-tabs", value="charts",
                children=[
                    dcc.Tab(label="Overview", value="overview", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="Charts", value="charts", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="Compare", value="compare", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="Dividends", value="dividends", className="tab", selected_className="tab--selected"),
                    dcc.Tab(label="History", value="history", className="tab", selected_className="tab--selected"),
                ], className="tabs"
            )
        ], className="top-right"),
    ], className="top-card"),

    html.Div(id="page-content"),
], className="app-container")

# ------------------ Tab rendering ------------------
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
                    html.H3("Key Metrics", className="section-label"),
                    html.Div([
                        html.Div([
                            html.Div([html.Span("PE Ratio", className="metric-label"),
                                      html.Span(id="pe-ratio", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Beta", className="metric-label"),
                                      html.Span(id="beta", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("52-Week Low", className="metric-label"),
                                      html.Span(id="week52-low", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Volume", className="metric-label"),
                                      html.Span(id="volume", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Open", className="metric-label"),
                                      html.Span(id="open", className="metric-value")], className="metric-card"),
                        ], className="metrics-col"),

                        html.Div([
                            html.Div([html.Span("Dividend Date", className="metric-label"),
                                      html.Span(id="dividend-date", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Earnings Date", className="metric-label"),
                                      html.Span(id="earnings-date", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("52-Week High", className="metric-label"),
                                      html.Span(id="week52-high", className="metric-value")], className="metric-card"),
                            html.Div([html.Span("Last Close", className="metric-label"),
                                      html.Span(id="last-close", className="metric-value")], className="metric-card"),
                        ], className="metrics-col"),
                    ], className="metrics-grid"),

                    html.Div([
                        html.H3("Analyst Recommendation", className="section-label"),
                        html.Span(id="analyst-opinion", className="analyst-value")
                    ], id="analyst-opinion-container", className="analyst-card", style={
                        "minHeight": "60px",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center",
                        "border": "2px solid #555",
                        "borderRadius": "8px",
                        "padding": "15px",
                        "marginTop": "20px"
                    })
                ], className="overview-left card"),

                html.Div([
                    html.H3("Close Price History", className="section-label"),
                    dcc.Loading(
                        id="loading-overview-graph",
                        type="circle",
                        children=dcc.Graph(id="overview-close-graph", className="overview-graph")
                    )
                ], className="overview-right card"),
            ], className="overview-container")
        ])

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

    elif tab == "compare":
        return html.Div([
            html.Div([
                html.Label("Select stocks to compare", className="section-label"),
                html.Div([
                    html.Div(id="compare-dropdown-container", className="compare-dropdowns"),
                    html.Button("Add Stock", id="add-stock-btn", n_clicks=0, className="add-stock-btn")
                ], className="compare-row"),
            ], className="card compare-options"),

            html.Div([
                dcc.Loading(
                    id="loading-compare-chart",
                    type="circle",
                    children=dcc.Graph(id="compare-chart", className="stock-graph"),
                )
            ], className="card"),
        ])

    elif tab == "dividends":
        return html.Div([html.Div([html.H3("Dividends coming soon...", className="section-label")], className="card")])

    elif tab == "history":
        return html.Div([html.Div([html.H3("History coming soon...", className="section-label")], className="card")])

    return html.Div()

# ------------------ Callbacks ------------------
# Overview metrics
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
            metrics["week52_low"], metrics["week52_high"]
        ]
    except Exception:
        return ["N/A"] * 9

# Analyst opinion
@app.callback(
    Output("analyst-opinion", "children"),
    Output("analyst-opinion", "style"),
    Output("analyst-opinion-container", "style"),
    Input("display-ticker-dropdown", "value")
)
def update_analyst_opinion(ticker_symbol):
    if not ticker_symbol:
        return "", {}, {}
    try:
        metrics = fetch_metrics(ticker_symbol)
        opinion = metrics["analyst"].upper()
        colors = {
            "STRONG_BUY": "#a8e6a2",
            "BUY": "#c7f2b4",
            "HOLD": "#f3e79b",
            "SELL": "#f7b6b6",
            "STRONG_SELL": "#f4a0a0"
        }
        color = colors.get(opinion, "white")
        text_style = {"color": color, "font-weight": "bold", "font-size": "1rem", "text-align": "center"}
        border_style = {
            "border": f"2px solid {color}",
            "border-radius": "8px",
            "padding": "15px",
            "display": "flex",
            "flex-direction": "column",
            "align-items": "center",
            "margin-top": "20px"
        }
        return opinion.replace("_", " "), text_style, border_style
    except Exception:
        return "N/A", {"color": "white", "text-align": "center"}, {"border": "2px solid #555"}

# Overview graph
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
            x=hist.index, y=hist["Close"],
            fill="tozeroy", line=dict(color="cyan", width=2), name="Close"
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
    Input("stock-chart", "relayoutData")
)
def update_chart(ticker_symbol, displayOptions, relayoutData):
    if not ticker_symbol:
        return no_update
    label = DEFAULT_LABEL_LOOKUP.get(ticker_symbol) or SEARCH_CACHE.get(ticker_symbol) or ticker_symbol
    label_with_ticker = f"{label} ({ticker_symbol})"
    return create_candlestick(ticker_symbol, label_with_ticker, relayoutData, displayOptions)

# Add dynamic compare dropdowns
@app.callback(
    Output("compare-dropdown-container", "children"),
    Input("add-stock-btn", "n_clicks"),
    State("compare-dropdown-container", "children")
)
def add_compare_dropdown(n_clicks, children):
    if children is None:
        children = []

    if n_clicks > 0:
        new_index = len(children)
        new_dropdown = dcc.Dropdown(
            id={"type": "compare-dropdown", "index": new_index},
            options=[{"label": f"{s['label']} ({s['value']})", "value": s["value"]} for s in DEFAULT_STOCKS],
            value=None,
            placeholder="Search for a stock...",
            searchable=True,
            clearable=True,
        )
        children.append(new_dropdown)
    return children


# Compare dropdown search callback
@app.callback(
    Output({"type": "compare-dropdown", "index": ALL}, "options"),
    Input({"type": "compare-dropdown", "index": ALL}, "search_value"),
    Input({"type": "compare-dropdown", "index": ALL}, "value")
)
def update_compare_options(search_values, selected_values):
    output_options = []

    for i, search_value in enumerate(search_values):
        options = []

        # Search via YahooQuery
        if search_value:
            try:
                results = search(search_value, first_quote=False, quotes_count=10).get("quotes", [])[:10]
                for q in results:
                    sym = q.get("symbol")
                    if not sym:
                        continue
                    label = q.get("shortname") or q.get("shortName") or sym
                    SEARCH_CACHE[sym] = label
                    options.append({"label": f"{label} ({sym})", "value": sym})
            except Exception:
                pass

        # Add default stocks if not already included
        existing_values = [opt["value"] for opt in options]
        default_options = [
            {"label": f"{s['label']} ({s['value']})", "value": s["value"]}
            for s in DEFAULT_STOCKS if s["value"] not in existing_values
        ]

        # Keep selected value visible
        sel_val = selected_values[i] if selected_values else None
        if sel_val and sel_val not in [opt["value"] for opt in options + default_options]:
            label = SEARCH_CACHE.get(sel_val, sel_val)
            options.append({"label": f"{label} ({sel_val})", "value": sel_val})

        output_options.append(options + default_options)

    return output_options


# Compare chart update (main stock + all compare dropdowns)
@app.callback(
    Output("compare-chart", "figure"),
    Input("display-ticker-dropdown", "value"),
    Input({"type": "compare-dropdown", "index": ALL}, "value")
)
def update_compare_chart(main_ticker, compare_tickers):
    tickers = [main_ticker] if main_ticker else []
    if compare_tickers:
        tickers += [t for t in compare_tickers if t]

    if not tickers:
        return go.Figure()

    fig = go.Figure()
    for ticker in tickers:
        try:
            hist = get_history(ticker)
            if hist.empty:
                continue
            pct_change = ((hist["Close"] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
            label = DEFAULT_LABEL_LOOKUP.get(ticker) or SEARCH_CACHE.get(ticker) or ticker
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=pct_change,
                mode="lines",
                name=f"{label} ({ticker})"
            ))
        except Exception:
            continue

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Date",
        yaxis_title="% Change",
        legend_title="Stocks",
        showlegend=True,
    )
    return fig

if __name__ == "__main__":
    app.run(debug=True)
