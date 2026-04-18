"""
Price Helper - A Python package for retrieving price data from Feather files.

This package provides utilities to fetch the closest price data for a given
timestamp and trading pair from .feather files.

Timezone handling:
- All input datetimes are assumed to be in local timezone (Australia/Sydney)
  if naive, or converted to local timezone if aware
- Internal searches are done in UTC
- Output datetimes are returned in local timezone (Australia/Sydney)
"""

from .core import (
    PriceHelper,
    ChainResolver,
    PriceNotFoundError,
)
from .api import (
    get_closest_price,
    get_closest_price_with_time,
    get_chained_price,
)
from .utils import (
    parse_pair,
    find_price_file,
    find_price_files_for_pair,
    to_local_timezone,
    to_utc,
    LOCAL_TIMEZONE,
)

__version__ = "0.2.0"
__author__ = "Alex Glebov + Claude Code"
__email__ = "python@iitsp.com.au"

__all__ = [
    # Core functions
    "get_closest_price",
    "get_closest_price_with_time",
    "get_chained_price",
    "PriceHelper",
    "ChainResolver",
    "PriceNotFoundError",
    # Utils
    "parse_pair",
    "find_price_file",
    "find_price_files_for_pair",
    "to_local_timezone",
    "to_utc",
    "LOCAL_TIMEZONE",
]
