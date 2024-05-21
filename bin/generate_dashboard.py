import sys
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table

"""
This script generates a dashboard from a TSV file.

Expected csv header: output from fastcat `per-read-stats.tsv`
read_id	filename	runid	sample_name	read_length	mean_quality	channel	read_number	start_time


Testing:

```
python generate_dashboard.py per_read_stats.tsv
```

"""


def generate_dashboard(per_read_stats_tsv):

    app = Dash(__name__)
    df = pd.read_csv(
        per_read_stats_tsv,
        sep="\t",
        compression="gzip",
    )

    # rename columns
    df = df.rename(
        columns={"read_length": "Read Length", "mean_quality": "Average QScore"}
    )

    app.layout = html.Div(
        [
            dcc.Dropdown(
                id="sample-dropdown",
                options=[{"label": i, "value": i} for i in df["sample_name"].unique()],
                value=df["sample_name"].unique().tolist(),
                multi=True,
            ),
            dcc.Graph(
                id="scatter-plot",
                figure=px.scatter(
                    df,
                    x="Read Length",
                    y="Average QScore",
                    color="sample_name",
                    title="Quality Score over Read Length",
                ),
            ),
            dash_table.DataTable(
                id="data-table",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),
                sort_action="native",  # Enable sorting
                sort_mode="multi",  # Allow multi-column sorting
            ),
        ]
    )

    @app.callback(Output("scatter-plot", "figure"), [Input("sample-dropdown", "value")])
    def update_graph(selected_samples):
        filtered_df = df[df["sample_name"].isin(selected_samples)]
        return px.scatter(
            filtered_df,
            x="Read Length",
            y="Average QScore",
            color="sample_name",
            title="Quality Score over Read Length",
        )

    @app.callback(Output("data-table", "data"), Input("scatter-plot", "selectedData"))
    def display_selected_data(selectedData):
        if selectedData:
            indices = [point["pointIndex"] for point in selectedData["points"]]
            filtered_df = df.iloc[indices]
            return filtered_df.to_dict("records")
        return df.to_dict("records")

    app.run_server(debug=True)


if __name__ == "__main__":
    csv_file = sys.argv[1]
    generate_dashboard(csv_file)
