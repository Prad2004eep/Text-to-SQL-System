"""Format query results for clean display."""

from __future__ import annotations

import pandas as pd


class ResultFormatter:
    """Format DataFrames for readable console and UI output."""

    def format(self, dataframe: pd.DataFrame) -> str:
        """Return a pretty-printed string representation."""
        if dataframe.empty:
            return "No results found."
        
        # Set display options for better formatting
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', 50)
        
        return dataframe.to_string(index=False, justify='center')
