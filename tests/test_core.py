"""Tests for core functionality."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from price_helper.core import PriceHelper, get_closest_price, PriceNotFoundError


class TestPriceHelper:
    """Test PriceHelper class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        helper = PriceHelper()
        assert helper.delimiter == "_"
        assert "price" in str(helper.price_dir).lower()

    def test_init_custom(self, tmp_path):
        """Test initialization with custom values."""
        helper = PriceHelper(
            price_dir=tmp_path,
            delimiter="-",
            timestamp_col="time",
            price_col="value"
        )
        assert helper.delimiter == "-"
        assert helper.price_dir == tmp_path
        assert helper.timestamp_col == "time"
        assert helper.price_col == "value"


class TestDetectColumns:
    """Test column auto-detection."""

    def test_detect_timestamp_column(self, tmp_path):
        """Test auto-detecting timestamp column."""
        helper = PriceHelper(price_dir=tmp_path)

        # Test with different column names
        df_datetime = pd.DataFrame({'datetime': [datetime.now()], 'price': [100.0]})
        df_timestamp = pd.DataFrame({'timestamp': [datetime.now()], 'price': [100.0]})
        df_time = pd.DataFrame({'time': [datetime.now()], 'price': [100.0]})

        assert helper._detect_column(df_datetime, helper.DEFAULT_TIMESTAMP_COLS, "timestamp") == 'datetime'
        assert helper._detect_column(df_timestamp, helper.DEFAULT_TIMESTAMP_COLS, "timestamp") == 'timestamp'
        assert helper._detect_column(df_time, helper.DEFAULT_TIMESTAMP_COLS, "timestamp") == 'time'

    def test_detect_price_column(self, tmp_path):
        """Test auto-detecting price column."""
        helper = PriceHelper(price_dir=tmp_path)

        df_price = pd.DataFrame({'timestamp': [datetime.now()], 'price': [100.0]})
        df_close = pd.DataFrame({'timestamp': [datetime.now()], 'close': [100.0]})
        df_value = pd.DataFrame({'timestamp': [datetime.now()], 'value': [100.0]})

        assert helper._detect_column(df_price, helper.DEFAULT_PRICE_COLS, "price") == 'price'
        assert helper._detect_column(df_close, helper.DEFAULT_PRICE_COLS, "price") == 'close'
        assert helper._detect_column(df_value, helper.DEFAULT_PRICE_COLS, "price") == 'value'


class TestFindClosestPriceInDataFrame:
    """Test finding closest price in DataFrame."""

    def test_find_closest(self, tmp_path):
        """Test finding closest price."""
        helper = PriceHelper(price_dir=tmp_path)

        # Create test data
        target_time = datetime(2024, 1, 15, 12, 30, 0)
        df = pd.DataFrame({
            'timestamp': [
                target_time - timedelta(minutes=5),
                target_time - timedelta(minutes=1),
                target_time + timedelta(minutes=2),
                target_time + timedelta(minutes=10),
            ],
            'price': [99.0, 100.0, 101.0, 102.0]
        })

        price = helper._find_closest_price_in_df(df, target_time)
        assert price == 100.0  # Closest is 1 minute before

    def test_find_closest_with_tolerance(self, tmp_path):
        """Test finding closest price with tolerance."""
        helper = PriceHelper(price_dir=tmp_path)

        target_time = datetime(2024, 1, 15, 12, 30, 0)
        df = pd.DataFrame({
            'timestamp': [
                target_time - timedelta(minutes=10),
                target_time + timedelta(minutes=10),
            ],
            'price': [99.0, 101.0]
        })

        # Should raise error if tolerance is too small
        with pytest.raises(PriceNotFoundError):
            helper._find_closest_price_in_df(df, target_time, tolerance_seconds=60)

        # Should succeed with larger tolerance
        price = helper._find_closest_price_in_df(df, target_time, tolerance_seconds=900)
        assert price in [99.0, 101.0]


class TestPriceNotFoundError:
    """Test PriceNotFoundError exception."""

    def test_error_message(self):
        """Test error message formatting."""
        error = PriceNotFoundError("Test message")
        assert str(error) == "Test message"
        assert isinstance(error, Exception)
