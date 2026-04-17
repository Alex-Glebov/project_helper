"""
Core functionality for price-helper package.

Handles loading feather files and retrieving closest price data for timestamps.
"""
import os
import re
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


class ChainResolver:
    """
    Resolver for finding price chains when direct pair data is not available.

    For example, if EUR_JPY is not available directly, it can be calculated as:
    EUR_JPY = EUR_USD * USD_JPY

    Or with longer chains:
    EUR_JPY = EUR_USD * USD_GBP * GBP_JPY
    """

    def __init__(
        self,
        price_dir: Union[str, Path] = "~/ollama/claudehome/price",
        delimiter: str = "_",
        max_chain_length: int = 4
    ):
        """
        Initialize ChainResolver.

        Args:
            price_dir: Directory containing .feather files
            delimiter: Delimiter for parsing pair strings
            max_chain_length: Maximum length of pair chain (default: 4)
        """
        self.price_dir = Path(price_dir).expanduser().resolve()
        self.delimiter = delimiter
        self.max_chain_length = max_chain_length
        self.helper = PriceHelper(price_dir=price_dir, delimiter=delimiter)
        self._cache = {}  # Cache for available pairs

    def _get_available_pairs(self, dt: Optional[datetime] = None) -> set:
        """
        Scan directory and get all available pair names.

        If dt is provided, only returns pairs that have data files
        covering the year and month of the requested date.

        Args:
            dt: Optional datetime to filter pairs by file date range

        Returns:
            Set of available pair strings
        """
        cache_key = f'pairs_{dt.strftime("%Y%m") if dt else "all"}'
        if self._cache.get(cache_key):
            return self._cache[cache_key]

        pairs = set()

        if not self.price_dir.exists():
            logger.warning(f"Price directory does not exist: {self.price_dir}")
            return pairs

        # If dt provided, extract year-month for filtering
        target_year_month = None
        if dt:
            dt_local = to_local_timezone(dt)
            target_year_month = dt_local.strftime("%Y-%m")
            logger.debug(f"Filtering pairs for year-month: {target_year_month}")

        for file_path in self.price_dir.glob("*-trades-*.feather"):
            # Extract pair from {pair}-trades-{date}.feather
            filename = file_path.stem
            match = re.match(r'^(.+?)-trades-', filename)
            if match:
                pair_name = match.group(1)
                if pair_name:
                    # If date filtering requested, check file covers target date
                    if target_year_month:
                        # Extract date from filename: {pair}-trades-{YYYY-MM-dd}
                        date_match = re.search(r'-trades-(\d{4})-(\d{2})-\d{2}$', filename)
                        if date_match:
                            file_year_month = f"{date_match.group(1)}-{date_match.group(2)}"
                            # Skip if file doesn't match target month
                            if file_year_month != target_year_month:
                                logger.debug(f"Skipping {filename}: {file_year_month} != {target_year_month}")
                                continue

                    pairs.add(pair_name)
                    # Also add the inverse pair
                    base, quote = parse_pair(pair_name, self.delimiter)
                    if base and quote:
                        inverse = f"{quote}{self.delimiter}{base}"
                        pairs.add(inverse)

        self._cache[cache_key] = pairs
        logger.debug(f"Found {len(pairs)} available pairs for {'date ' + target_year_month if target_year_month else 'all dates'}")
        return pairs

    def _get_price_direct(
        self,
        dt: datetime,
        pair: str,
        tolerance_seconds: Optional[int] = None
    ) -> Optional[float]:
        """
        Try to get price directly from file.

        Returns:
            Price if found, None otherwise
        """
        try:
            return self.helper.get_closest_price(dt, pair, tolerance_seconds)
        except PriceNotFoundError:
            return None

    def _get_price_or_inverse(
        self,
        dt: datetime,
        pair: str,
        tolerance_seconds: Optional[int] = None
    ) -> tuple:
        """
        Get price, trying direct and inverse pairs.

        For pair "A_B", also tries "B_A" and returns 1/price.

        Returns:
            Tuple of (price, is_inverse) or (None, False) if not found
        """
        # Try direct
        price = self._get_price_direct(dt, pair, tolerance_seconds)
        if price is not None:
            return price, False

        # Try inverse
        base, quote = parse_pair(pair, self.delimiter)
        if base and quote:
            inverse_pair = f"{quote}{self.delimiter}{base}"
            price = self._get_price_direct(dt, inverse_pair, tolerance_seconds)
            if price is not None:
                return 1.0 / price, True

        return None, False

    def find_chain(
        self,
        target_pair: str,
        dt: Optional[datetime] = None,
        visited: Optional[set] = None,
        current_path: Optional[list] = None,
        depth: int = 0
    ) -> Optional[list]:
        """
        Recursively find a chain of pairs to calculate target pair.

        If dt is provided, only considers pairs with data files
        covering the year and month of the requested date.

        Args:
            target_pair: The desired pair (e.g., "EUR_JPY")
            dt: Optional datetime to filter pairs by file date
            visited: Set of visited currencies (for cycle detection)
            current_path: Current chain of pairs being built
            depth: Current recursion depth

        Returns:
            List of pairs forming the chain, or None if no chain found
        """
        import re

        if visited is None:
            visited = set()
        if current_path is None:
            current_path = []

        # Check max depth
        if depth >= self.max_chain_length:
            return None

        target_base, target_quote = parse_pair(target_pair, self.delimiter)

        if not target_base or not target_quote:
            return None

        # Get available pairs, filtered by date if provided
        available_pairs = self._get_available_pairs(dt)

        # Check if we can get this pair directly
        if target_pair in available_pairs:
            return current_path + [target_pair]

        # Check if inverse is available
        inverse_pair = f"{target_quote}{self.delimiter}{target_base}"
        if inverse_pair in available_pairs:
            # Will be handled by _get_price_or_inverse
            return current_path + [target_pair]

        # Mark current base as visited to prevent cycles
        visited.add(target_base)

        # Find all pairs that start with target_base
        # or all pairs that end with target_quote
        candidates = []

        for pair in available_pairs:
            base, quote = parse_pair(pair, self.delimiter)
            if not base or not quote:
                continue

            # Look for pairs that can extend our chain
            # We want: target_base -> X and X -> target_quote
            if base == target_base and quote not in visited:
                candidates.append((pair, quote, target_quote))
            elif quote == target_quote and base not in visited:
                candidates.append((pair, target_base, base))

        # Try each candidate
        for pair, next_base, next_quote in candidates:
            next_pair = f"{next_base}{self.delimiter}{next_quote}"

            # Recursively find chain from next currency to target
            new_path = current_path + [pair]
            result = self.find_chain(
                next_pair,
                dt,
                visited.copy(),
                new_path,
                depth + 1
            )

            if result is not None:
                return result

        return None

    def get_chained_price(
        self,
        dt: datetime,
        pair: str,
        tolerance_seconds: Optional[int] = None
    ) -> float:
        """
        Get price using chain of pairs when direct data is not available.

        For example:
        - EUR_JPY = EUR_USD * USD_JPY
        - EUR_GBP = EUR_USD * USD_GBP
        - EUR_JPY = EUR_USD * USD_GBP * GBP_JPY (longer chain)

        Args:
            dt: Target datetime
            pair: Trading pair string (e.g., "EUR_JPY")
            tolerance_seconds: Maximum allowed difference per pair

        Returns:
            Calculated price

        Raises:
            PriceNotFoundError: If no chain can be found
        """
        # Convert to local for logging
        dt_local = to_local_timezone(dt)
        logger.info(f"Looking for chained price: {pair} at {dt_local}")

        # First try direct price
        direct_price = self._get_price_or_inverse(dt, pair, tolerance_seconds)
        if direct_price[0] is not None:
            logger.info(f"Found direct price for {pair}: {direct_price[0]}")
            return direct_price[0]

        # Find chain with date filtering
        chain = self.find_chain(pair, dt)

        if not chain:
            raise PriceNotFoundError(
                f"No direct price or chain found for {pair}. "
                f"Tried max chain length: {self.max_chain_length}"
            )

        logger.info(f"Found chain for {pair}: {' -> '.join(chain)}")

        # Calculate price by multiplying along chain
        total_price = 1.0
        actual_chain = []

        for i, pair_in_chain in enumerate(chain):
            price, is_inverse = self._get_price_or_inverse(
                dt, pair_in_chain, tolerance_seconds
            )

            if price is None:
                raise PriceNotFoundError(
                    f"Chain failed at step {i+1}: {pair_in_chain} not available"
                )

            total_price *= price
            actual_chain.append(f"{pair_in_chain}{'(inv)' if is_inverse else ''}")

        logger.info(
            f"Calculated {pair} = {total_price:.6f} from chain: "
            f"{' * '.join(actual_chain)}"
        )

        return total_price


def get_chained_price(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None,
    max_chain_length: int = 4
) -> float:
    """
    Convenience function to get chained price for a pair.

    Tries direct price first, then falls back to chain calculation.

    Args:
        dt: Target datetime
        pair: Trading pair string
        price_dir: Directory containing .feather files
        delimiter: Delimiter for parsing pair strings
        tolerance_seconds: Maximum allowed difference per pair
        max_chain_length: Maximum number of pairs in chain (default: 4)

    Returns:
        Price value (direct or calculated)

    Raises:
        PriceNotFoundError: If no direct price or chain can be found

    Example:
        >>> from datetime import datetime
        >>> # If EUR_JPY not available directly, but EUR_USD and USD_JPY are:
        >>> price = get_chained_price(
        ...     dt=datetime(2024, 1, 15, 12, 30),
        ...     pair="EUR_JPY"
        ... )

        # Calculates: EUR_JPY = EUR_USD * USD_JPY
    """
    resolver = ChainResolver(
        price_dir=price_dir,
        delimiter=delimiter,
        max_chain_length=max_chain_length
    )
    return resolver.get_chained_price(dt, pair, tolerance_seconds)
