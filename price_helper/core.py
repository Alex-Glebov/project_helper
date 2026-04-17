"""
Core functionality for price-helper package.

Handles loading feather files and retrieving closest price data for timestamps.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import logging

import pandas as pd

from .utils import parse_pair, find_price_file

logger = logging.getLogger(__name__)


class PriceNotFoundError(Exception):
    """Raised when price data cannot be found for the given parameters."""
    pass


class PriceHelper:
    """
    Helper class for retrieving price data from feather files.

    Attributes:
        price_dir: Path to the directory containing price .feather files
        delimiter: Delimiter used to parse pair strings
        timestamp_col: Name of the timestamp column in feather files
        price_col: Name of the price column to retrieve
    """

    DEFAULT_TIMESTAMP_COLS = ['timestamp', 'datetime', 'time', 'dt']
    DEFAULT_PRICE_COLS = ['price', 'close', 'value', 'last']

    def __init__(
        self,
        price_dir: Union[str, Path] = "~/ollama/claudehome/price",
        delimiter: str = "_",
        timestamp_col: Optional[str] = None,
        price_col: Optional[str] = None
    ):
        """
        Initialize PriceHelper.

        Args:
            price_dir: Directory containing .feather files (default: ~/ollama/claudehome/price)
            delimiter: Delimiter for parsing pair strings (default: "_")
            timestamp_col: Column name for timestamps (auto-detected if None)
            price_col: Column name for prices (auto-detected if None)
        """
        self.price_dir = Path(price_dir).expanduser().resolve()
        self.delimiter = delimiter
        self._timestamp_col = timestamp_col
        self._price_col = price_col

        # Ensure directory exists
        if not self.price_dir.exists():
            logger.warning(f"Price directory does not exist: {self.price_dir}")

    @property
    def timestamp_col(self) -> str:
        """Get timestamp column name (auto-detect if not set)."""
        return self._timestamp_col or 'timestamp'

    @timestamp_col.setter
    def timestamp_col(self, value: str):
        self._timestamp_col = value

    @property
    def price_col(self) -> str:
        """Get price column name (auto-detect if not set)."""
        return self._price_col or 'price'

    @price_col.setter
    def price_col(self, value: str):
        self._price_col = value

    def get_closest_price(
        self,
        dt: datetime,
        pair: str,
        tolerance_seconds: Optional[int] = None
    ) -> float:
        """
        Get the closest price for a given timestamp and pair.

        Args:
            dt: Target datetime
            pair: Trading pair string (e.g., "BTC_USD")
            tolerance_seconds: Maximum allowed difference in seconds (optional)

        Returns:
            The closest price value

        Raises:
            PriceNotFoundError: If no price file found or no data within tolerance
        """
        logger.debug(f"Looking for price: pair={pair}, dt={dt}")

        # Find the correct file
        file_path = find_price_file(
            pair=pair,
            dt=dt,
            price_dir=self.price_dir,
            delimiter=self.delimiter
        )

        if not file_path or not file_path.exists():
            raise PriceNotFoundError(
                f"No price file found for pair '{pair}' at {dt}. "
                f"Searched in: {self.price_dir}"
            )

        logger.debug(f"Found price file: {file_path}")

        # Load the data
        try:
            df = pd.read_feather(file_path)
        except Exception as e:
            logger.error(f"Failed to load feather file {file_path}: {e}")
            raise PriceNotFoundError(f"Could not load price data: {e}")

        return self._find_closest_price_in_df(df, dt, tolerance_seconds)

    def _find_closest_price_in_df(
        self,
        df: pd.DataFrame,
        dt: datetime,
        tolerance_seconds: Optional[int] = None
    ) -> float:
        """
        Find the closest price in a DataFrame for a given timestamp.

        Args:
            df: DataFrame with price data
            dt: Target datetime
            tolerance_seconds: Maximum allowed difference in seconds

        Returns:
            Closest price value
        """
        # Auto-detect timestamp column
        timestamp_col = self._detect_column(df, self.DEFAULT_TIMESTAMP_COLS, "timestamp")
        if not timestamp_col:
            raise PriceNotFoundError(
                f"No timestamp column found. Tried: {self.DEFAULT_TIMESTAMP_COLS}"
            )

        # Ensure timestamp column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
            try:
                df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            except Exception as e:
                raise PriceNotFoundError(f"Could not parse timestamps: {e}")

        # Calculate time differences
        df['_diff'] = (df[timestamp_col] - pd.Timestamp(dt)).abs()

        # Check tolerance if specified
        if tolerance_seconds is not None:
            min_diff = df['_diff'].min().total_seconds()
            if min_diff > tolerance_seconds:
                raise PriceNotFoundError(
                    f"No price found within {tolerance_seconds}s tolerance. "
                    f"Closest was {min_diff:.1f}s away."
                )

        # Find closest row
        idx = df['_diff'].idxmin()
        closest_row = df.loc[idx]

        # Auto-detect price column
        price_col = self._detect_column(df, self.DEFAULT_PRICE_COLS, "price")
        if not price_col:
            raise PriceNotFoundError(
                f"No price column found. Tried: {self.DEFAULT_PRICE_COLS}"
            )

        price = closest_row[price_col]

        logger.info(
            f"Found closest price: {price} at {closest_row[timestamp_col]} "
            f"(diff: {closest_row['_diff']})"
        )

        return float(price)

    def _detect_column(self, df: pd.DataFrame, candidates: list, col_type: str) -> Optional[str]:
        """
        Detect column name from candidate list.

        Args:
            df: DataFrame to search
            candidates: List of candidate column names
            col_type: Type of column for error messages

        Returns:
            Detected column name or None
        """
        # Check if explicitly set
        if col_type == "timestamp" and self._timestamp_col:
            if self._timestamp_col in df.columns:
                return self._timestamp_col
        if col_type == "price" and self._price_col:
            if self._price_col in df.columns:
                return self._price_col

        # Try candidates
        for col in candidates:
            if col in df.columns:
                return col
            # Try case-insensitive match
            for df_col in df.columns:
                if col.lower() == df_col.lower():
                    return df_col

        return None

    def get_price_range(
        self,
        pair: str,
        start_dt: datetime,
        end_dt: datetime
    ) -> pd.DataFrame:
        """
        Get price data for a time range.

        Args:
            pair: Trading pair string
            start_dt: Start datetime
            end_dt: End datetime

        Returns:
            DataFrame with price data in the range
        """
        # This would need to load multiple files if range spans months
        # For now, just load the start month file and filter
        file_path = find_price_file(
            pair=pair,
            dt=start_dt,
            price_dir=self.price_dir,
            delimiter=self.delimiter
        )

        if not file_path or not file_path.exists():
            raise PriceNotFoundError(f"No price file found for pair '{pair}'")

        df = pd.read_feather(file_path)
        timestamp_col = self._detect_column(df, self.DEFAULT_TIMESTAMP_COLS, "timestamp")

        if timestamp_col:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            mask = (df[timestamp_col] >= start_dt) & (df[timestamp_col] <= end_dt)
            return df[mask]

        return df


# Convenience function for simple use cases
def get_closest_price(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None
) -> float:
    """
    Convenience function to get the closest price for a timestamp and pair.

    Args:
        dt: Target datetime
        pair: Trading pair string
        price_dir: Directory containing .feather files
        delimiter: Delimiter for parsing pair strings
        tolerance_seconds: Maximum allowed difference in seconds

    Returns:
        Closest price value

    Raises:
        PriceNotFoundError: If price cannot be found

    Example:
        >>> from datetime import datetime
        >>> price = get_closest_price(
        ...     dt=datetime(2024, 1, 15, 12, 30),
        ...     pair="BTC_USD"
        ... )
    """
    helper = PriceHelper(price_dir=price_dir, delimiter=delimiter)
    return helper.get_closest_price(dt, pair, tolerance_seconds)
