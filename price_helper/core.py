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
import pytz

from .utils import (
    parse_pair,
    find_price_file,
    find_price_files_for_pair,
    to_local_timezone,
    to_utc,
    LOCAL_TIMEZONE,
)

logger = logging.getLogger(__name__)


class PriceNotFoundError(Exception):
    """Raised when price data cannot be found for the given parameters."""
    pass


class PriceHelper:
    """
    Helper class for retrieving price data from feather files.

    Timezone handling:
    - Input datetimes are converted to UTC for searching
    - Output datetimes are returned in local timezone (Australia/Sydney)
    - File dates in filenames are in local timezone

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

        logger.info(f"PriceHelper initialized with timezone: {LOCAL_TIMEZONE}")

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

        Input datetime is converted to UTC for searching.
        The file is selected based on the UTC timestamp.

        Args:
            dt: Target datetime (naive assumed local, aware converted to local)
            pair: Trading pair string (e.g., "BTC_USD")
            tolerance_seconds: Maximum allowed difference in seconds (optional)

        Returns:
            The closest price value

        Raises:
            PriceNotFoundError: If no price file found or no data within tolerance
        """
        # Convert input to local timezone for logging, then to UTC for searching
        dt_local = to_local_timezone(dt)
        dt_utc = to_utc(dt)

        logger.info(f"Looking for price: pair={pair}, local={dt_local}, utc={dt_utc}")

        # Find the correct file (searches using UTC timestamp)
        file_path = find_price_file(
            pair=pair,
            dt=dt,
            price_dir=self.price_dir,
            delimiter=self.delimiter
        )

        if not file_path or not file_path.exists():
            raise PriceNotFoundError(
                f"No price file found for pair '{pair}' at {dt_local}. "
                f"Searched in: {self.price_dir}"
            )

        logger.info(f"Found price file: {file_path}")

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
            dt: Target datetime (will be converted to UTC for comparison)
            tolerance_seconds: Maximum allowed difference in seconds

        Returns:
            Closest price value
        """
        # Convert target to UTC for comparison
        dt_utc = to_utc(dt)

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

        # Ensure timestamps are timezone-aware (assume UTC if naive)
        if df[timestamp_col].dt.tz is None:
            logger.debug("Timestamps are naive, assuming UTC")
            df[timestamp_col] = df[timestamp_col].dt.tz_localize(pytz.UTC)

        # Calculate time differences using UTC
        df['_diff'] = (df[timestamp_col] - pd.Timestamp(dt_utc)).abs()

        # Check tolerance if specified
        if tolerance_seconds is not None:
            min_diff_seconds = df['_diff'].min().total_seconds()
            if min_diff_seconds > tolerance_seconds:
                dt_local = to_local_timezone(dt)
                raise PriceNotFoundError(
                    f"No price found within {tolerance_seconds}s tolerance. "
                    f"Closest was {min_diff_seconds:.1f}s away at {dt_local}."
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

        # Get timestamp in local timezone for logging
        closest_ts_utc = closest_row[timestamp_col]
        if hasattr(closest_ts_utc, 'to_pydatetime'):
            closest_ts_utc = closest_ts_utc.to_pydatetime()
        closest_ts_local = to_local_timezone(closest_ts_utc)

        logger.info(
            f"Found closest price: {price} at {closest_ts_local} local "
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

        Input datetimes are converted to UTC for searching.
        Returns DataFrame with timestamps in local timezone.

        Args:
            pair: Trading pair string
            start_dt: Start datetime
            end_dt: End datetime

        Returns:
            DataFrame with price data in the range
        """
        # Convert to UTC for searching
        start_utc = to_utc(start_dt)
        end_utc = to_utc(end_dt)

        logger.info(f"Getting price range: {pair} from {start_utc} to {end_utc} UTC")

        # Find files that cover the range
        files = find_price_files_for_pair(pair, self.price_dir, self.delimiter)

        if not files:
            raise PriceNotFoundError(f"No price files found for pair '{pair}'")

        # Load and combine data from relevant files
        all_data = []
        for file_path, file_start_local in files:
            file_start_utc = to_utc(file_start_local)

            # Skip files that are completely after the end time
            # or completely before the start time
            # (Would need file end date to do this properly)
            try:
                df = pd.read_feather(file_path)
                all_data.append(df)
            except Exception as e:
                logger.warning(f"Could not load {file_path}: {e}")

        if not all_data:
            raise PriceNotFoundError(f"Could not load any data for {pair}")

        # Combine data
        combined = pd.concat(all_data, ignore_index=True)

        # Detect timestamp column
        timestamp_col = self._detect_column(combined, self.DEFAULT_TIMESTAMP_COLS, "timestamp")

        if timestamp_col:
            combined[timestamp_col] = pd.to_datetime(combined[timestamp_col])

            # Ensure UTC for filtering
            if combined[timestamp_col].dt.tz is None:
                combined[timestamp_col] = combined[timestamp_col].dt.tz_localize(pytz.UTC)

            # Filter by UTC times
            mask = (combined[timestamp_col] >= start_utc) & (combined[timestamp_col] <= end_utc)
            result = combined[mask].copy()

            # Convert timestamps to local timezone for return
            if result[timestamp_col].dt.tz is not None:
                result[timestamp_col] = result[timestamp_col].dt.tz_convert(LOCAL_TIMEZONE)

            return result

        return combined


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

    Input datetime is converted to UTC for searching.
    The result is the closest price from the data file.

    Args:
        dt: Target datetime (naive assumed local, aware converted appropriately)
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


def get_closest_price_with_time(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None
) -> tuple:
    """
    Get the closest price and its timestamp for a given datetime and pair.

    Returns both the price and the actual timestamp (in local timezone).

    Args:
        dt: Target datetime
        pair: Trading pair string
        price_dir: Directory containing .feather files
        delimiter: Delimiter for parsing pair strings
        tolerance_seconds: Maximum allowed difference in seconds

    Returns:
        Tuple of (price, timestamp_in_local_tz)

    Raises:
        PriceNotFoundError: If price cannot be found
    """
    helper = PriceHelper(price_dir=price_dir, delimiter=delimiter)

    # Convert input to UTC for searching
    dt_utc = to_utc(dt)

    # Find file
    file_path = find_price_file(
        pair=pair,
        dt=dt,
        price_dir=Path(price_dir).expanduser().resolve(),
        delimiter=delimiter
    )

    if not file_path or not file_path.exists():
        raise PriceNotFoundError(f"No price file found for {pair}")

    # Load data
    df = pd.read_feather(file_path)

    # Detect columns
    timestamp_col = helper._detect_column(df, helper.DEFAULT_TIMESTAMP_COLS, "timestamp")
    price_col = helper._detect_column(df, helper.DEFAULT_PRICE_COLS, "price")

    if not timestamp_col or not price_col:
        raise PriceNotFoundError("Required columns not found")

    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])

    if df[timestamp_col].dt.tz is None:
        df[timestamp_col] = df[timestamp_col].dt.tz_localize(pytz.UTC)

    # Find closest
    df['_diff'] = (df[timestamp_col] - pd.Timestamp(dt_utc)).abs()

    if tolerance_seconds:
        min_diff = df['_diff'].min().total_seconds()
        if min_diff > tolerance_seconds:
            raise PriceNotFoundError(f"No price within {tolerance_seconds}s tolerance")

    idx = df['_diff'].idxmin()
    closest_row = df.loc[idx]

    price = float(closest_row[price_col])

    # Convert timestamp to local timezone
    closest_ts_utc = closest_row[timestamp_col]
    if hasattr(closest_ts_utc, 'to_pydatetime'):
        closest_ts_utc = closest_ts_utc.to_pydatetime()
    closest_ts_local = to_local_timezone(closest_ts_utc)

    return price, closest_ts_local
