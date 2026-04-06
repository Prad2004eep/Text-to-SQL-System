"""Automatic chart generation for query results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import plotly.express as px
from plotly.graph_objs import Figure


@dataclass
class VisualizationResult:
    """Chart metadata and figure for a query result set."""

    figure: Figure
    chart_type: str
    x_column: str
    y_column: str


class VisualizationBuilder:
    """Create a default visualization from a DataFrame when possible."""

    def build(self, dataframe: pd.DataFrame) -> Optional[VisualizationResult]:
        """Return a bar or line chart when the results contain plottable columns."""
        if dataframe.empty or len(dataframe.columns) < 2:
            return None

        numeric_columns = list(dataframe.select_dtypes(include=["number"]).columns)
        if not numeric_columns:
            return None

        y_column = numeric_columns[0]
        x_column = next((column for column in dataframe.columns if column != y_column), dataframe.columns[0])

        datetime_series = pd.to_datetime(dataframe[x_column], errors="coerce")
        if datetime_series.notna().sum() >= max(2, len(dataframe) // 2):
            plot_frame = dataframe.copy()
            plot_frame[x_column] = datetime_series
            figure = px.line(plot_frame, x=x_column, y=y_column, markers=True, title=f"{y_column} over {x_column}")
            return VisualizationResult(figure=figure, chart_type="line", x_column=x_column, y_column=y_column)

        figure = px.bar(dataframe, x=x_column, y=y_column, title=f"{y_column} by {x_column}")
        return VisualizationResult(figure=figure, chart_type="bar", x_column=x_column, y_column=y_column)
