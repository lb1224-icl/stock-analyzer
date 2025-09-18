from dash import dcc, Input, Output
from yahooquery import search

DEFAULT_STOCKS = [
    {"label": "Apple", "value": "AAPL"},
    {"label": "Microsoft", "value": "MSFT"},
    {"label": "Amazon", "value": "AMZN"},
    {"label": "Tesla", "value": "TSLA"},
    {"label": "NVIDIA", "value": "NVDA"},
    {"label": "Google", "value": "GOOGL"},
    {"label": "Meta", "value": "META"},
]

SEARCH_CACHE = {}

class StockDropdown:
    def __init__(self, app, component_id=None, index=None):
        self.app = app
        if component_id:
            self.component_id = component_id
        elif index is not None:
            self.component_id = {"type": "compare-dropdown", "index": index}
        else:
            raise ValueError("Must provide component_id or index")
        if isinstance(self.component_id, str):
            self.register_callback()

    def render(self):
        return dcc.Dropdown(
            id=self.component_id,
            options=[
                {"label": f"{s['label']} ({s['value']})", "value": s["value"]}
                for s in DEFAULT_STOCKS
            ],
            value="AAPL" if self.component_id == "display-ticker-dropdown" else None,
            placeholder="Search for a stock...",
            clearable=False if self.component_id == "display-ticker-dropdown" else True,
            searchable=True,
        )

    def register_callback(self):
        # Only main ticker dropdown uses callback
        @self.app.callback(
            Output(self.component_id, "options"),
            Input(self.component_id, "search_value"),
            Input(self.component_id, "value"),
        )
        def update_main_options(search_value, selected_value):
            return self._generate_options(search_value, selected_value)

    def _generate_options(self, search_value, selected_value):
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

        # Add default stocks if not already in search results
        existing_values = [opt["value"] for opt in search_options]
        default_options = [
            {"label": f"{s['label']} ({s['value']})", "value": s["value"]}
            for s in DEFAULT_STOCKS if s["value"] not in existing_values
        ]

        # Ensure selected value stays visible
        if selected_value and selected_value not in [opt["value"] for opt in search_options + default_options]:
            label = SEARCH_CACHE.get(selected_value, selected_value)
            search_options.append({"label": f"{label} ({selected_value})", "value": selected_value})

        return search_options + default_options
