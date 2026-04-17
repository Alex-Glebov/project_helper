"""Pytest configuration and fixtures."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


@pytest.fixture
def sample_price_data():
    """Create sample price data for testing."""
    base_time = datetime(2024, 1, 15, 0, 0, 0)
    return pd.DataFrame({
        'timestamp': [base_time + timedelta(minutes=i*5) for i in range(288)],  # 24 hours, every 5 minutes
        'price': [100.0 + i * 0.1 for i in range(288)],
    })


@pytest.fixture
def temp_price_dir(tmp_path):
    """Create a temporary price directory with sample data."""
    price_dir = tmp_path / "price"
    price_dir.mkdir()

    # Create sample feather files
    base_time = datetime(2024, 1, 15, 0, 0, 0)

    for day in range(1, 3):
        df = pd.DataFrame({
            'timestamp': [datetime(2024, 1, day, i, j, 0)
                          for i in range(24) for j in range(0, 60, 5)],
            'price': [100.0 + i * 0.01 for i in range(288)],
        })

        file_path = price_dir / f"BTC_USD_2024010{day}.feather"
        df.to_feather(file_path)

    return price_dir
