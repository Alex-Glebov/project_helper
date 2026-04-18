"""
Standalone API functions for price-helper package.

These are convenience wrappers around the PriceHelper and ChainResolver classes.
For advanced usage, use the classes directly.
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Tuple

from .core import PriceHelper, ChainResolver, PriceNotFoundError
from .utils import to_local_timezone


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
        >>> from price_helper import get_closest_price
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
) -> Tuple[float, datetime]:
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
    from .utils import find_price_file
    import pandas as pd
    import pytz

    helper = PriceHelper(price_dir=price_dir, delimiter=delimiter)

    # Convert input to UTC for searching
    from .utils import to_utc
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
        # NOTE: Pandas timestamps have nanosecond precision, but Python datetime
        # only supports microsecond precision. The conversion may lose sub-microsecond
        # precision. We suppress the UserWarning as this is a known limitation.
        # See: pandas.Timestamp.to_pydatetime() documentation
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            closest_ts_utc = closest_ts_utc.to_pydatetime()
    closest_ts_local = to_local_timezone(closest_ts_utc)

    return price, closest_ts_local


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
        >>> from price_helper import get_chained_price
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


# Make PriceNotFoundError available from this module for convenience
__all__ = [
    'get_closest_price',
    'get_closest_price_with_time',
    'get_chained_price',
    'PriceNotFoundError',
]
