"""
Utility functions for price-helper package.

Handles pair parsing, file path resolution, and other helper functions.
"""
import os
import re
from datetime import datetime, timedelta
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


def parse_filename_date(filename: str) -> Optional[Tuple[datetime, int]]:
    """
    Parse date and month count from filename.

    Filename format: {pair}-trades-{YYYY-MM-dd}.feather
    where:
    - YYYY-MM is the year and month
    - dd is the number of months covered (01 means 1 month, 03 means 3 months)
    The date is in local timezone (Australia/Sydney).

    Args:
        filename: Name of the file (without extension)

    Returns:
        Tuple of (start_date, months_covered) or None if not found
        start_date is the first day of the starting month in local timezone
    """
    # Look for date pattern YYYY-MM-DD where DD is months covered
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        months_covered = int(match.group(3))

        # Create start date (first day of month) in local timezone
        start_date = datetime(year, month, 1, 0, 0, 0)
        return LOCAL_TIMEZONE.localize(start_date), months_covered
    return None


def get_file_end_date(start_date: datetime, months_covered: int) -> datetime:
    """
    Calculate the end date for a file based on start date and months covered.

    Args:
        start_date: Start date (first day of starting month)
        months_covered: Number of months covered

    Returns:
        End date (exclusive - first day after coverage ends)
    """
    # Calculate end month
    total_months = (start_date.year * 12 + start_date.month - 1) + months_covered
    end_year = total_months // 12
    end_month = (total_months % 12) + 1

    # Return first day of month after coverage ends
    end_date = datetime(end_year, end_month, 1, 0, 0, 0)
    return LOCAL_TIMEZONE.localize(end_date)


def find_price_files_for_pair(
    pair: str,
    price_dir: Path,
    delimiter: str = "_"
) -> List[Tuple[Path, datetime, int]]:
    """
    Find all price files for a given pair.

    File naming: {pair}-trades-{YYYY-MM-dd}.feather
    where dd is the number of months covered.

    Args:
        pair: Trading pair string (e.g., "BTC_USD")
        price_dir: Directory containing price files
        delimiter: Delimiter for parsing pair

    Returns:
        List of tuples (file_path, start_date, months_covered)
    """
    base, quote = parse_pair(pair, delimiter)

    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    files = []

    # Build search pattern: {pair}-trades-*.feather
    pattern = f"{pair}-trades-*.feather"

    for file_path in price_dir.glob(pattern):
        result = parse_filename_date(file_path.stem)
        if result:
            start_date, months_covered = result
            files.append((file_path, start_date, months_covered))

    # Also try without the pair prefix if no files found
    if not files:
        # Try matching by base symbol only
        for file_path in price_dir.glob("*-trades-*.feather"):
            if base.lower() in file_path.stem.lower():
                result = parse_filename_date(file_path.stem)
                if result:
                    start_date, months_covered = result
                    files.append((file_path, start_date, months_covered))

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
    where dd is the number of months covered.

    Strategy:
    1. First look for file with start month = requested month, day = 01
    2. If not found, look for multi-month files (day > 01) that cover the date

    Args:
        pair: Trading pair string (e.g., "BTC_USD")
        dt: Target datetime
        price_dir: Directory containing price files
        delimiter: Delimiter for parsing pair

    Returns:
        Path to the price file, or None if not found
    """
    # Convert input datetime to local timezone
    dt_local = to_local_timezone(dt)
    target_year = dt_local.year
    target_month = dt_local.month

    logger.debug(f"Searching for {pair} data at local time: {dt_local}")

    # Find all files for this pair
    files = find_price_files_for_pair(pair, price_dir, delimiter)

    if not files:
        logger.warning(f"No price files found for {pair} in {price_dir}")
        return None

    logger.debug(f"Found {len(files)} files for {pair}")

    # Step 1: Look for exact month match with day = 01 (single month file)
    for file_path, start_date, months_covered in files:
        if (start_date.year == target_year and
            start_date.month == target_month and
            months_covered == 1):
            logger.debug(f"Found exact month file: {file_path}")
            return file_path

    # Step 2: Look for multi-month files that cover the target date
    for file_path, start_date, months_covered in files:
        if months_covered > 1:
            end_date = get_file_end_date(start_date, months_covered)
            # Check if target date is within [start_date, end_date)
            if start_date <= dt_local < end_date:
                logger.debug(f"Found multi-month file covering date: {file_path}")
                return file_path

    # Step 3: If no specific match, use file with matching start month (even if multi-month)
    for file_path, start_date, months_covered in files:
        if start_date.year == target_year and start_date.month == target_month:
            logger.debug(f"Using file with matching start month: {file_path}")
            return file_path

    # Step 4: Use the file whose start date is closest before target
    for i in range(len(files) - 1, -1, -1):
        file_path, start_date, months_covered = files[i]
        if start_date <= dt_local:
            logger.debug(f"Using closest file before target: {file_path}")
            return file_path

    # Step 5: Fall back to first file
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
        List of tuples (start_date, months_covered) as strings
    """
    if not price_dir.exists():
        logger.warning(f"Price directory does not exist: {price_dir}")
        return []

    ranges = []

    for file_path in price_dir.glob("*-trades-*.feather"):
        filename = file_path.stem

        # Check pair filter if provided
        if pair:
            base = get_base_symbol(pair, delimiter)
            if pair not in filename and base.lower() not in filename.lower():
                continue

        # Extract date
        result = parse_filename_date(filename)
        if result:
            start_date, months_covered = result
            end_date = get_file_end_date(start_date, months_covered)
            ranges.append({
                'start': start_date.strftime('%Y-%m-%d'),
                'months': months_covered,
                'end': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
            })

    return sorted(ranges, key=lambda x: x['start'])


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
