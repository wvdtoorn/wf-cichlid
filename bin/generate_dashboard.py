import sys
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table, callback_context

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
            html.Div(
                html.Button(
                    "Close Dashboard",
                    id="close-button",
                    style={
                        "color": "white",
                        "background-color": "red",
                        "font-size": "20px",
                        "padding": "10px 20px",
                    },
                ),
                style={"textAlign": "right"},
            ),
            html.H3("Overview Table"),
            dash_table.DataTable(
                id="overview-table",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),
                sort_action="native",
                sort_mode="multi",
                filter_action="native",  # Enable filtering
            ),
            html.H3("Interactive Analysis"),
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
            html.H4("Data Table for Selected Samples"),
            dash_table.DataTable(
                id="filtered-data-table",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),  # Initially show all data
                sort_action="native",
                sort_mode="multi",
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

    @app.callback(
        Output("filtered-data-table", "data"),
        [
            Input("sample-dropdown", "value"),
            Input("scatter-plot", "relayoutData"),
            Input("scatter-plot", "selectedData"),
        ],
    )
    def update_filtered_table(selected_samples, relayoutData, selectedData):

        # Filter DataFrame based on selected samples from the dropdown
        filtered_df = df[df["sample_name"].isin(selected_samples)]

        # Check if the callback was triggered by a change in the dropdown
        if (
            callback_context.triggered
            and callback_context.triggered[0]["prop_id"] == "sample-dropdown.value"
        ):
            # Reset any zoom filtering as the plot zooms out
            relayoutData = None

        # Apply zoom filtering if zoom level changes are detected in relayoutData
        if relayoutData:
            if "xaxis.range[0]" in relayoutData and "xaxis.range[1]" in relayoutData:
                x0, x1 = relayoutData["xaxis.range[0]"], relayoutData["xaxis.range[1]"]
                filtered_df = filtered_df[
                    (filtered_df["Read Length"] >= x0)
                    & (filtered_df["Read Length"] <= x1)
                ]

            if "yaxis.range[0]" in relayoutData and "yaxis.range[1]" in relayoutData:
                y0, y1 = relayoutData["yaxis.range[0]"], relayoutData["yaxis.range[1]"]
                filtered_df = filtered_df[
                    (filtered_df["Average QScore"] >= y0)
                    & (filtered_df["Average QScore"] <= y1)
                ]

        # Apply filtering based on selected hue labels in the scatter plot
        # TODO: implement this

        return filtered_df.to_dict("records")

    @app.callback(
        Output("close-button", "n_clicks"),  # Dummy output
        [Input("close-button", "n_clicks")],
    )
    def close_dashboard(n_clicks):
        if n_clicks:
            with open(dashboard_closed_file, "w") as file:
                file.write("Dashboard was closed at: " + str(pd.Timestamp.now()))
        return None

    app.run_server(debug=True)


if __name__ == "__main__":
    csv_file = sys.argv[1]
    generate_dashboard(csv_file)
