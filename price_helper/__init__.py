"""
Price Helper - A Python package for retrieving price data from Feather files.

This package provides utilities to fetch the closest price data for a given
timestamp and trading pair from .feather files.
"""

from .core import get_closest_price, PriceHelper, PriceNotFoundError
from .utils import parse_pair, find_price_file

__version__ = "0.1.0"
__author__ = "Alex Glebov + Claude code"
__email__ = "python@iitsp.com.au"

__all__ = [
    "get_closest_price",
    "PriceHelper",
    "PriceNotFoundError",
    "parse_pair",
    "find_price_file",
]
