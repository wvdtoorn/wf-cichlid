import os
import sys
import pandas as pd
import plotly.express as px
from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    dash_table,
    callback_context,
    no_update,
    State,
)
from plotly.io import write_image

"""
This script generates a dashboard from a TSV file.

Expected csv header: output from fastcat `per-read-stats.tsv`
read_id	filename	runid	sample_name	read_length	mean_quality	channel	read_number	start_time


Testing:

```
python generate_dashboard.py per_read_stats.tsv
```

"""


def generate_dashboard(
    per_read_stats_tsv: str,
    dashboard_closed_file: str = "dashboard_closed",
    mid_threshold: int = 5000,
    long_threshold: int = 10000,
):
    """Generate an interactive dashboard from a TSV file containing per-read statistics.

    Parameters
    ----------
    per_read_stats_tsv : str
        Path to the TSV file containing per-read statistics.
    dashboard_closed_file : str, optional
        Path to the file that will be created when the dashboard is closed, by default 'dashboard_closed'.

    Returns
    -------
    None
    """

    app = Dash(__name__)
    df = pd.read_csv(
        per_read_stats_tsv,
        sep="\t",
        compression="gzip" if per_read_stats_tsv.endswith(".gz") else None,
    )

    # rename columns
    df = df.rename(
        columns={"read_length": "Read Length", "mean_quality": "Average QScore"}
    )

    # Create a color map for sample names
    sample_names = df["sample_name"].unique()
    colors = px.colors.qualitative.Plotly  # Using Plotly's qualitative color scale
    color_map = {name: colors[i % len(colors)] for i, name in enumerate(sample_names)}

    # Define categories for read length
    df["Read Length Category"] = pd.cut(
        df["Read Length"],
        bins=[0, mid_threshold, long_threshold, float("inf")],
        labels=["short reads", "mid reads", "long reads"],
    )

    app.layout = html.Div(
        [
            html.Div(
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
                    html.Div(
                        [
                            dcc.Input(
                                id="save-plot-dir-input",
                                type="text",
                                placeholder="Enter path to plot directory",
                            ),
                            html.Button(
                                "Export Plots",
                                id="export-button",
                                n_clicks=0,
                                style={
                                    "color": "white",
                                    "background-color": "blue",
                                    "font-size": "20px",
                                    "padding": "10px 20px",
                                },
                            ),
                        ],
                        style={"textAlign": "right"},
                    ),
                ]
            ),
            html.Details(
                [
                    html.Summary("Data Table"),
                    dash_table.DataTable(
                        id="overview-table",
                        columns=[{"name": i, "id": i} for i in df.columns],
                        data=df.to_dict("records"),
                        sort_action="native",
                        sort_mode="multi",
                        filter_action="native",  # Enable filtering
                    ),
                ]
            ),
            html.H3("Interactive Analysis"),
            dcc.Dropdown(
                id="sample-dropdown",
                options=[{"label": i, "value": i} for i in df["sample_name"].unique()],
                value=df["sample_name"].unique().tolist(),
                multi=True,
            ),
            html.Button("Select All", id="select-all-button", n_clicks=0),
            html.Button("Deselect All", id="deselect-all-button", n_clicks=0),
            dcc.Graph(
                id="scatter-plot-read-length-qscore",
                figure=px.scatter(
                    df,
                    x="Read Length",
                    y="Average QScore",
                    color="sample_name",
                    color_discrete_map=color_map,
                    title="Quality Score over Read Length",
                    marginal_x="histogram",
                    marginal_y="histogram",
                ),
            ),
            html.Details(
                [
                    html.Summary("Data Table for Scatterplot"),
                    html.Div(
                        [
                            dcc.Input(
                                id="save-path-input",
                                type="text",
                                placeholder="Enter save path here",
                            ),
                            html.Button(
                                "Export Read IDs",
                                id="export-read-ids-button",
                                n_clicks=0,
                            ),
                        ]
                    ),
                    dash_table.DataTable(
                        id="filtered-data-table",
                        columns=[{"name": i, "id": i} for i in df.columns],
                        data=df.to_dict("records"),  # Initially show all data
                        sort_action="native",
                        sort_mode="multi",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Mid Read Length Threshold:"),
                            dcc.Input(
                                id="mid-threshold", type="number", value=mid_threshold
                            ),
                        ],
                        style={"padding": "10px"},
                    ),
                    html.Div(
                        [
                            html.Label("Long Read Length Threshold:"),
                            dcc.Input(
                                id="long-threshold", type="number", value=long_threshold
                            ),
                        ],
                        style={"padding": "10px"},
                    ),
                ],
                style={
                    "padding": "20px",
                    "max-width": "400px",
                    "display": "flex",
                    "flexDirection": "column",
                },
            ),
            dcc.Graph(
                id="violin-plot-qscore-read-length",
                figure=px.violin(
                    df,
                    x="sample_name",
                    y="Average QScore",
                    color="sample_name",
                    color_discrete_map=color_map,
                    facet_row="Read Length Category",  # Facet into rows based on read length categories
                    title="Quality Score over Read Length by Sample",
                    points="all",
                    box=True,
                ),
            ),
            dcc.Graph(
                id="violin-plot-read-length",
                figure=px.violin(
                    df,
                    x="sample_name",
                    y="Read Length",
                    color="sample_name",
                    color_discrete_map=color_map,
                    title="Read Length by Sample",
                    points="all",
                    box=True,
                ),
            ),
        ]
    )

    @app.callback(
        Output("violin-plot-qscore-read-length", "figure"),
        [
            Input("mid-threshold", "value"),
            Input("long-threshold", "value"),
            Input("sample-dropdown", "value"),
        ],
    )
    def update_violin_plot_qscore_read_length(
        mid_threshold, long_threshold, selected_samples
    ):
        if not selected_samples:
            return px.violin()

        # Filter DataFrame based on selected samples
        filtered_df = df[df["sample_name"].isin(selected_samples)]

        # Update the DataFrame with new thresholds for read length categories
        filtered_df["Read Length Category"] = pd.cut(
            filtered_df["Read Length"],
            bins=[0, mid_threshold, long_threshold, float("inf")],
            labels=["short reads", "mid reads", "long reads"],
        )

        # Calculate the number of unique categories for setting plot height
        num_categories = len(filtered_df["Read Length Category"].unique())
        plot_height = max(300, 200 * num_categories)

        fig = px.violin(
            filtered_df,
            x="sample_name",
            y="Average QScore",
            color="sample_name",
            color_discrete_map=color_map,
            facet_row="Read Length Category",
            title="Quality Score over Read Length by Sample",
            height=plot_height,
            points="all",
            box=True,
        )

        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1].strip()))

        fig.update_layout(margin=dict(l=40, r=40, t=40, b=80))

        return fig

    @app.callback(
        Output("scatter-plot-read-length-qscore", "figure"),
        [
            Input("sample-dropdown", "value"),
            Input("scatter-plot-read-length-qscore", "relayoutData"),
        ],
    )
    def update_graph(selected_samples, relayoutData):
        filtered_df = df[df["sample_name"].isin(selected_samples)]

        # Check if there is zoom data in relayoutData
        if (
            relayoutData
            and "xaxis.range[0]" in relayoutData
            and "yaxis.range[0]" in relayoutData
        ):
            x0, x1 = relayoutData["xaxis.range[0]"], relayoutData["xaxis.range[1]"]
            y0, y1 = relayoutData["yaxis.range[0]"], relayoutData["yaxis.range[1]"]
            filtered_df = filtered_df[
                (filtered_df["Read Length"] >= x0)
                & (filtered_df["Read Length"] <= x1)
                & (filtered_df["Average QScore"] >= y0)
                & (filtered_df["Average QScore"] <= y1)
            ]

        return px.scatter(
            filtered_df,
            x="Read Length",
            y="Average QScore",
            color="sample_name",
            color_discrete_map=color_map,
            title="Quality Score over Read Length",
            marginal_x="histogram",
            marginal_y="histogram",
        )

    @app.callback(
        Output("filtered-data-table", "data"),
        [
            Input("sample-dropdown", "value"),
            Input("scatter-plot-read-length-qscore", "relayoutData"),
            Input("scatter-plot-read-length-qscore", "selectedData"),
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
        Output("sample-dropdown", "value"),
        [
            Input("select-all-button", "n_clicks"),
            Input("deselect-all-button", "n_clicks"),
        ],
        [State("sample-dropdown", "options")],
    )
    def update_dropdown(select_all_clicks, deselect_all_clicks, options):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if button_id == "select-all-button":
            return [option["value"] for option in options]
        elif button_id == "deselect-all-button":
            return []
        return no_update

    @app.callback(
        Output("export-button", "children"),
        [Input("export-button", "n_clicks")],
        [
            State("scatter-plot-read-length-qscore", "figure"),
            State("violin-plot-qscore-read-length", "figure"),
            State("violin-plot-read-length", "figure"),
            State("sample-dropdown", "value"),
            State("save-plot-dir-input", "value"),
        ],
        prevent_initial_call=True,
    )
    def export_results(
        n_clicks,
        scatter_qscore_read_length_fig,
        violin_qscore_read_length_fig,
        violin_read_length_fig,
        selected_samples,
        save_path,
    ):
        if n_clicks:
            if not save_path:
                return html.Div(
                    [
                        dcc.ConfirmDialog(
                            displayed=True,
                            message="No save path provided, skipping export.",
                        ),
                        "Export Plots",  # Maintain the original button text
                    ]
                )

            selected_samples_str = (
                "_".join(selected_samples) if selected_samples else "all_samples"
            )
            scatter_qscore_read_length_path = (
                f"{selected_samples_str}--qscore_read_length_scatter_plot.png"
            )
            violin_qscore_read_length_path = (
                f"{selected_samples_str}--qscore_read_length_violin_plot.png"
            )
            violin_read_length_path = (
                f"{selected_samples_str}--read_length_violin_plot.png"
            )

            os.makedirs(save_path, exist_ok=True)

            try:
                write_image(
                    scatter_qscore_read_length_fig,
                    os.path.join(save_path, scatter_qscore_read_length_path),
                )
                write_image(
                    violin_qscore_read_length_fig,
                    os.path.join(save_path, violin_qscore_read_length_path),
                )
                write_image(
                    violin_read_length_fig,
                    os.path.join(save_path, violin_read_length_path),
                )
            except Exception as e:
                print(f"Failed to save plot images: {e}")

        return "Export Plots"  # Always return the original button text

    @app.callback(
        Output("export-read-ids-button", "n_clicks"),  # Dummy output
        [Input("export-read-ids-button", "n_clicks")],
        [
            State("overview-table", "derived_virtual_data"),
            State("save-path-input", "value"),
        ],
        prevent_initial_call=True,
    )
    def export_read_ids(n_clicks, rows, save_path):
        if n_clicks > 0 and save_path:
            read_ids = [row["read_id"] for row in rows] if rows else []
            try:
                with open(save_path, "w") as file:
                    file.write("\n".join(read_ids))
            except Exception as e:
                print(f"Error writing to file: {e}")
        return None

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
