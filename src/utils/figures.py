import plotly.graph_objs as go
import pandas as pd

def empty_fig(title, message, chart_type="Chart"):
    fig = go.Figure()
    fig.add_annotation(
        text=f"⚠️ {message}",
        xref="paper", yref="paper", x=0.5, y=0.5,
        showarrow=False, font=dict(size=20, color="red")
    )
    fig.update_layout(title=f"{title} {chart_type}", template="plotly_dark")
    return fig

def handle_yrange(data, relayoutData):
    low_col = "Low" if "Low" in data.columns else "Close"
    high_col = "High" if "High" in data.columns else "Close"

    if relayoutData and "xaxis.range[0]" in relayoutData:
        start = pd.to_datetime(relayoutData["xaxis.range[0]"])
        end = pd.to_datetime(relayoutData["xaxis.range[1]"])
        if data.index.tz is not None:
            start, end = start.tz_localize(data.index.tz), end.tz_localize(data.index.tz)
        visible = data.loc[start:end]
        if not visible.empty:
            y_min, y_max = max(visible[low_col].min(), 0), visible[high_col].max()
        else:
            y_min, y_max = data[low_col].min(), data[high_col].max()
    else:
        y_min, y_max = data[low_col].min(), data[high_col].max()

    span = y_max - y_min if y_max != y_min else y_max * 0.05
    return [y_min - span * 0.05, y_max + span * 0.05]
