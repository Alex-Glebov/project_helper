"""
Utility functions for price-helper package.

Handles pair parsing, file path resolution, and other helper functions.
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def parse_pair(pair: str, delimiter: str = "_") -> tuple:
    """
    Parse a pair string into base and quote components.

    Args:
        pair: Pair string (e.g., "BTC_USD", "ETH-USD")
        delimiter: Delimiter used in the pair string (default: "_")

    Returns:
        Tuple of (base, quote) strings

    Example:
        >>> parse_pair("BTC_USD")
        ('BTC', 'USD')
        >>> parse_pair("ETH-USD", delimiter="-")
        ('ETH', 'USD')
    """
    parts = pair.split(delimiter)

    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        # Single component - treat as base with empty quote
        return parts[0], ""
    else:
        return pair, ""


def get_base_symbol(pair: str, delimiter: str = "_") -> str:
    """
    Get the base symbol from a pair string.

    Args:
        pair: Pair string (e.g., "BTC_USD")
        delimiter: Delimiter used in the pair string

    Returns:
        Base symbol (first component)
    """
    return parse_pair(pair, delimiter)[0]


def get_quote_symbol(pair: str, delimiter: str = "_") -> str:
    """
    Get the quote symbol from a pair string.

    Args:
        pair: Pair string (e.g., "BTC_USD")
        delimiter: Delimiter used in the pair string

    Returns:
        Quote symbol (second component)
    """
    return parse_pair(pair, delimiter)[1]


def build_filename_pattern(base: str, year_month: str) -> str:
    """
    Build a filename pattern for searching price files.

    File naming convention:
    - Files start with the pair name (base symbol)
    - End with the covered month (YYYYMM)
    - Extension is .feather

    Args:
        base: Base symbol (e.g., "BTC")
        year_month: Year-month string (e.g., "202401")

    Returns:
        Filename pattern for glob search
    """
    return f"{base}*{year_month}.feather"


def find_price_file(
    pair: str,
    dt: datetime,
    price_dir: Path,
    delimiter: str = "_"
) -> Optional[Path]:
    """
    Find the price file for a given pair and datetime.

    Searches for .feather files matching the pattern:
    {base}*{YYYYMM}.feather

    Args:
        pair: Trading pair string (e.g., "BTC_USD")
        dt: Target datetime
        price_dir: Directory containing price files
        delimiter: Delimiter for parsing pair

    Returns:
        Path to the price file, or None if not found
    """
    base, quote = parse_pair(pair, delimiter)
    year_month = dt.strftime("%Y%m")

    logger.debug(f"Searching for {pair} data in {price_dir} for {year_month}")

    # Build search patterns
    patterns = [
        f"{base}*{year_month}.feather",
        f"{base}_{quote}*{year_month}.feather",
        f"{base}_{quote}_{year_month}.feather",
        f"{base}*{quote}*{year_month}.feather",
    ]

    # Search for files
    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return None

    # Try each pattern
    for pattern in patterns:
        matches = list(price_dir.glob(pattern))
        if matches:
            # Return first match (most specific pattern should match first)
            logger.debug(f"Found {len(matches)} files matching pattern: {pattern}")
            return matches[0]

    # Try to list all files and find a match
    all_feather_files = list(price_dir.glob("*.feather"))
    logger.debug(f"Total .feather files in directory: {len(all_feather_files)}")

    for file_path in all_feather_files:
        filename = file_path.stem.lower()
        # Check if base symbol is in filename and year_month is at the end
        if base.lower() in filename and filename.endswith(year_month):
            logger.debug(f"Found matching file: {file_path}")
            return file_path

    logger.warning(
        f"No price file found for {pair} in {year_month}. "
        f"Tried patterns: {patterns}"
    )
    return None


def list_available_pairs(price_dir: Path, delimiter: str = "_") -> list:
    """
    List all available trading pairs in the price directory.

    Args:
        price_dir: Directory containing price files
        delimiter: Delimiter used in pair names

    Returns:
        List of unique pair strings
    """
    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    pairs = set()

    for file_path in price_dir.glob("*.feather"):
        # Try to extract pair from filename
        # Expected format: {pair}_{YYYYMM}.feather or variations
        filename = file_path.stem

        # Remove year_month suffix (8 digits at end)
        match = re.match(r'^(.*?)(?:_\d{8})?$', filename)
        if match:
            pair_name = match.group(1)
            if pair_name:
                pairs.add(pair_name)

    return sorted(list(pairs))


def list_available_months(
    price_dir: Path,
    pair: Optional[str] = None,
    delimiter: str = "_"
) -> list:
    """
    List all available months for a given pair.

    Args:
        price_dir: Directory containing price files
        pair: Optional pair filter (if None, lists all months)
        delimiter: Delimiter used in pair names

    Returns:
        List of year-month strings (e.g., ["202401", "202402"])
    """
    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    months = set()

    for file_path in price_dir.glob("*.feather"):
        filename = file_path.stem

        # Extract year_month from end of filename (8 digits)
        match = re.search(r'(\d{8})$', filename)
        if match:
            year_month = match.group(1)

            if pair:
                # Filter by pair
                base = get_base_symbol(pair, delimiter)
                if base.lower() in filename.lower():
                    months.add(year_month)
            else:
                months.add(year_month)

    return sorted(list(months))


def validate_price_directory(price_dir: Path) -> bool:
    """
    Validate that the price directory exists and contains .feather files.

    Args:
        price_dir: Directory to validate

    Returns:
        True if valid, False otherwise
    """
    if not price_dir.exists():
        logger.error(f"Price directory does not exist: {price_dir}")
        return False

    if not price_dir.is_dir():
        logger.error(f"Price path is not a directory: {price_dir}")
        return False

    feather_files = list(price_dir.glob("*.feather"))
    if not feather_files:
        logger.warning(f"No .feather files found in {price_dir}")
        return False

    logger.info(f"Found {len(feather_files)} .feather files in {price_dir}")
    return True
