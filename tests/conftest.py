"""Pytest configuration and fixtures."""
import pytest
import pandas as pd
import pytz
from datetime import datetime, timedelta
from pathlib import Path

from price_helper.utils import LOCAL_TIMEZONE


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    base_time = datetime(2024, 1, 15, 0, 0, 0)
    # Create timezone-aware timestamps in local timezone
    timestamps = [LOCAL_TIMEZONE.localize(base_time + timedelta(minutes=i*5)) for i in range(288)]
    return pd.DataFrame({
        'timestamp': timestamps,
        'price': [100.0 + i * 0.1 for i in range(288)],
    })


@pytest.fixture
def temp_price_dir(tmp_path):
    """Create a temporary price directory with sample data."""
    price_dir = tmp_path / "price"
    price_dir.mkdir()

    # Create sample feather files with new naming convention:
    # {pair}-trades-{YYYY-MM-dd}.feather where dd = months covered
    # Example: BTC_USD-trades-2024-01-01.feather = Jan 2024, 1 month
    #          BTC_USD-trades-2024-01-03.feather = Jan-Mar 2024, 3 months

    # File 1: January 2024, single month (01)
    timestamps = [LOCAL_TIMEZONE.localize(datetime(2024, 1, day, i, j, 0))
                  for day in range(1, 32)
                  for i in range(24) for j in range(0, 60, 5)]

    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': [100.0 + i * 0.01 for i in range(len(timestamps))],
    })
    file_path = price_dir / "BTC_USD-trades-2024-01-01.feather"
    df.to_feather(file_path)

    # File 2: February 2024, single month (01)
    timestamps = [LOCAL_TIMEZONE.localize(datetime(2024, 2, day, i, j, 0))
                  for day in range(1, 29)
                  for i in range(24) for j in range(0, 60, 5)]

    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': [100.0 + i * 0.01 for i in range(len(timestamps))],
    })
    file_path = price_dir / "BTC_USD-trades-2024-02-01.feather"
    df.to_feather(file_path)

    # File 3: Multi-month file covering March-May 2024 (03 = 3 months)
    timestamps = []
    for month in range(3, 6):  # March, April, May
        days_in_month = 31 if month in [3, 5] else 30
        for day in range(1, days_in_month + 1):
            for i in range(24):
                for j in range(0, 60, 30):
                    timestamps.append(LOCAL_TIMEZONE.localize(datetime(2024, month, day, i, j, 0)))

    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': [100.0 + i * 0.01 for i in range(len(timestamps))],
    })
    file_path = price_dir / "BTC_USD-trades-2024-03-03.feather"
    df.to_feather(file_path)

    return price_dir
