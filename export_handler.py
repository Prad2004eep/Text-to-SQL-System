"""Helpers for exporting query results to downloadable formats."""

from __future__ import annotations

from io import BytesIO

import pandas as pd


class ExportHandler:
    """Create export payloads for tabular query results."""

    def to_csv_bytes(self, dataframe: pd.DataFrame) -> bytes:
        """Serialize a DataFrame to UTF-8 CSV bytes."""
        return dataframe.to_csv(index=False).encode("utf-8")

    def to_excel_bytes(self, dataframe: pd.DataFrame) -> bytes:
        """Serialize a DataFrame to Excel bytes."""
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Results")
        return buffer.getvalue()
