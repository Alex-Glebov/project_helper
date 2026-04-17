"""
Utility functions for price-helper package.

Handles pair parsing, file path resolution, and other helper functions.
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
import logging

import pytz

logger = logging.getLogger(__name__)

# Default timezone - Australia/Sydney
LOCAL_TIMEZONE = pytz.timezone('Australia/Sydney')


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


def to_local_timezone(dt: datetime) -> datetime:
    """
    Convert datetime to local timezone (Australia/Sydney).

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Datetime in local timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in local timezone
        dt = LOCAL_TIMEZONE.localize(dt)
    else:
        # Convert to local timezone
        dt = dt.astimezone(LOCAL_TIMEZONE)
    return dt


def to_utc(dt: datetime) -> datetime:
    """
    Convert datetime to UTC.

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Datetime in UTC
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in local timezone
        dt = LOCAL_TIMEZONE.localize(dt)
    # Convert to UTC
    return dt.astimezone(pytz.UTC)


def parse_filename_date(filename: str) -> Optional[datetime]:
    """
    Parse date from filename.

    Filename format: {pair}-trades-{YYYY-MM-dd}.feather
    where dd is the number of months in the file.
    The date is in local timezone (Australia/Sydney).

    Args:
        filename: Name of the file (without extension)

    Returns:
        Datetime object in local timezone, or None if not found
    """
    # Look for date pattern YYYY-MM-DD
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        # Create datetime in local timezone
        dt = datetime(year, month, day, 0, 0, 0)
        return LOCAL_TIMEZONE.localize(dt)
    return None


def find_price_files_for_pair(
    pair: str,
    price_dir: Path,
    delimiter: str = "_"
) -> List[Tuple[Path, datetime]]:
    """
    Find all price files for a given pair.

    File naming: {pair}-trades-{YYYY-MM-dd}.feather

    Args:
        pair: Trading pair string (e.g., "BTC_USD")
        price_dir: Directory containing price files
        delimiter: Delimiter for parsing pair

    Returns:
        List of tuples (file_path, start_date_in_local_tz)
    """
    base, quote = parse_pair(pair, delimiter)

    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    files = []

    # Build search pattern: {pair}-trades-*.feather
    pattern = f"{pair}-trades-*.feather"

    for file_path in price_dir.glob(pattern):
        start_date = parse_filename_date(file_path.stem)
        if start_date:
            files.append((file_path, start_date))

    # Also try without the pair prefix if no files found
    if not files:
        # Try matching by base symbol only
        for file_path in price_dir.glob("*-trades-*.feather"):
            if base.lower() in file_path.stem.lower():
                start_date = parse_filename_date(file_path.stem)
                if start_date:
                    files.append((file_path, start_date))

    # Sort by start date
    files.sort(key=lambda x: x[1])

    return files


def find_price_file(
    pair: str,
    dt: datetime,
    price_dir: Path,
    delimiter: str = "_"
) -> Optional[Path]:
    """
    Find the price file for a given pair and datetime.

    File naming: {pair}-trades-{YYYY-MM-dd}.feather
    where dd is the number of months in the file.

    The datetime is converted to UTC for searching, but the filename
    date is in local timezone (Australia/Sydney).

    Args:
        pair: Trading pair string (e.g., "BTC_USD")
        dt: Target datetime (will be converted to UTC)
        price_dir: Directory containing price files
        delimiter: Delimiter for parsing pair

    Returns:
        Path to the price file, or None if not found
    """
    # Convert input datetime to UTC for searching
    dt_utc = to_utc(dt)

    logger.debug(f"Searching for {pair} data at UTC: {dt_utc}")

    # Find all files for this pair
    files = find_price_files_for_pair(pair, price_dir, delimiter)

    if not files:
        logger.warning(f"No price files found for {pair} in {price_dir}")
        return None

    logger.debug(f"Found {len(files)} files for {pair}")

    # Find the file that contains the target datetime
    # File start dates are in local timezone
    for i, (file_path, start_date_local) in enumerate(files):
        # Convert file start date to UTC for comparison
        start_date_utc = to_utc(start_date_local)

        # Check if this file contains the target datetime
        # If it's the last file, use it
        if i == len(files) - 1:
            logger.debug(f"Using last file: {file_path}")
            return file_path

        # Get next file start date
        next_start_date_utc = to_utc(files[i + 1][1])

        # Check if target is within this file's range
        if start_date_utc <= dt_utc < next_start_date_utc:
            logger.debug(f"Found matching file: {file_path}")
            return file_path

    # If target is before first file, use first file
    if files:
        logger.debug(f"Using first file: {files[0][0]}")
        return files[0][0]

    return None


def list_available_pairs(price_dir: Path, delimiter: str = "_") -> list:
    """
    List all available trading pairs in the price directory.

    Extracts pair names from files matching pattern: *-trades-*.feather

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

    for file_path in price_dir.glob("*-trades-*.feather"):
        filename = file_path.stem
        # Extract pair from {pair}-trades-{date}
        match = re.match(r'^(.+?)-trades-', filename)
        if match:
            pair_name = match.group(1)
            if pair_name:
                pairs.add(pair_name)

    return sorted(list(pairs))


def list_available_date_ranges(
    price_dir: Path,
    pair: Optional[str] = None,
    delimiter: str = "_"
) -> list:
    """
    List all available date ranges for a given pair.

    Returns dates in local timezone (Australia/Sydney).

    Args:
        price_dir: Directory containing price files
        pair: Optional pair filter (if None, lists all)
        delimiter: Delimiter used in pair names

    Returns:
        List of start date strings (YYYY-MM-DD) in local timezone
    """
    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    dates = []

    for file_path in price_dir.glob("*-trades-*.feather"):
        filename = file_path.stem

        # Check pair filter if provided
        if pair:
            base = get_base_symbol(pair, delimiter)
            if pair not in filename and base.lower() not in filename.lower():
                continue

        # Extract date
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            dates.append(match.group(0))

    return sorted(list(set(dates)))


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
