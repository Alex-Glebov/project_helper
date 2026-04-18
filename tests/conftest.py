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

    # Create sample feather files with NEW naming convention:
    # {pair}-trades-{YYYY-MM-dd}.feather

    for day in range(1, 3):
        # Create timestamps in local timezone
        timestamps = [LOCAL_TIMEZONE.localize(datetime(2024, 1, day, i, j, 0))
                      for i in range(24) for j in range(0, 60, 5)]

        df = pd.DataFrame({
            'timestamp': timestamps,
            'price': [100.0 + i * 0.01 for i in range(288)],
        })

        # New naming: BTC_USD-trades-2024-01-01.feather
        file_path = price_dir / f"BTC_USD-trades-2024-01-0{day}.feather"
        df.to_feather(file_path)

    return price_dir
