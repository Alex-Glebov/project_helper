"""Tests for utility functions."""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import pytz

from price_helper.utils import (
    parse_pair,
    get_base_symbol,
    get_quote_symbol,
    to_local_timezone,
    to_utc,
    parse_filename_date,
    get_file_end_date,
    find_price_file,
    find_price_files_for_pair,
    list_available_pairs,
    list_available_date_ranges,
    LOCAL_TIMEZONE,
)


class TestParsePair:
    """Test pair parsing functions."""

    def test_parse_pair_standard(self):
        """Test parsing standard pair format."""
        base, quote = parse_pair("BTC_USD")
        assert base == "BTC"
        assert quote == "USD"

    def test_parse_pair_custom_delimiter(self):
        """Test parsing with custom delimiter."""
        base, quote = parse_pair("ETH-USD", delimiter="-")
        assert base == "ETH"
        assert quote == "USD"

    def test_parse_pair_single_component(self):
        """Test parsing pair with only one component."""
        base, quote = parse_pair("BTC")
        assert base == "BTC"
        assert quote == ""

    def test_parse_pair_multiple_components(self):
        """Test parsing pair with multiple components."""
        base, quote = parse_pair("BTC_USD_SPOT")
        assert base == "BTC"
        assert quote == "USD"


class TestGetSymbols:
    """Test symbol extraction functions."""

    def test_get_base_symbol(self):
        """Test extracting base symbol."""
        assert get_base_symbol("BTC_USD") == "BTC"
        assert get_base_symbol("ETH-USD", delimiter="-") == "ETH"

    def test_get_quote_symbol(self):
        """Test extracting quote symbol."""
        assert get_quote_symbol("BTC_USD") == "USD"
        assert get_quote_symbol("ETH-USD", delimiter="-") == "USD"


class TestTimezoneConversion:
    """Test timezone conversion functions."""

    def test_to_local_timezone(self):
        """Test converting to local timezone."""
        # Test with naive datetime (assumed local)
        dt_naive = datetime(2024, 1, 15, 12, 0, 0)
        dt_local = to_local_timezone(dt_naive)
        assert dt_local.tzinfo is not None
        assert dt_local.tzinfo.zone == 'Australia/Sydney'

    def test_to_utc(self):
        """Test converting to UTC."""
        # Test with naive datetime (assumed local)
        dt_naive = datetime(2024, 1, 15, 12, 0, 0)
        dt_utc = to_utc(dt_naive)
        assert dt_utc.tzinfo is not None
        assert dt_utc.tzinfo == pytz.UTC

    def test_timezone_conversion_roundtrip(self):
        """Test that timezone conversions are consistent."""
        dt_naive = datetime(2024, 1, 15, 12, 0, 0)
        dt_utc = to_utc(dt_naive)
        dt_local = to_local_timezone(dt_utc)
        assert dt_local.tzinfo.zone == 'Australia/Sydney'


class TestParseFilenameDate:
    """Test filename date parsing."""

    def test_parse_standard_filename(self):
        """Test parsing standard filename format."""
        result = parse_filename_date("BTC_USD-trades-2024-01-15")
        assert result is not None
        start_date, months_covered = result
        assert start_date.year == 2024
        assert start_date.month == 1
        assert months_covered == 15  # dd = months covered
        assert start_date.tzinfo.zone == 'Australia/Sydney'

    def test_parse_single_month_filename(self):
        """Test parsing single month file."""
        result = parse_filename_date("BTC_USD-trades-2024-03-01")
        assert result is not None
        start_date, months_covered = result
        assert months_covered == 1

    def test_parse_filename_no_date(self):
        """Test parsing filename without date."""
        result = parse_filename_date("BTC_USD-trades")
        assert result is None


class TestFileEndDate:
    """Test end date calculation for files."""

    def test_single_month_end_date(self):
        """Test end date for single month file."""
        start_date = LOCAL_TIMEZONE.localize(datetime(2024, 1, 1, 0, 0, 0))
        end_date = get_file_end_date(start_date, 1)
        assert end_date.year == 2024
        assert end_date.month == 2
        assert end_date.day == 1

    def test_three_month_end_date(self):
        """Test end date for 3 month file."""
        start_date = LOCAL_TIMEZONE.localize(datetime(2024, 1, 1, 0, 0, 0))
        end_date = get_file_end_date(start_date, 3)
        assert end_date.year == 2024
        assert end_date.month == 4
        assert end_date.day == 1


class TestFindPriceFiles:
    """Test finding price files."""

    def test_find_files_for_pair(self, tmp_path):
        """Test finding files for a pair."""
        # Create test files with month coverage
        (tmp_path / "BTC_USD-trades-2024-01-01.feather").touch()  # Jan
        (tmp_path / "BTC_USD-trades-2024-02-03.feather").touch()  # Feb-Apr
        (tmp_path / "ETH_USD-trades-2024-01-01.feather").touch()

        files = find_price_files_for_pair("BTC_USD", tmp_path)
        assert len(files) == 2

    def test_find_price_file_exact_month(self, tmp_path):
        """Test finding file for exact month (day=01)."""
        (tmp_path / "BTC_USD-trades-2024-01-01.feather").touch()  # Jan only
        (tmp_path / "BTC_USD-trades-2024-02-03.feather").touch()  # Feb-Apr

        target = datetime(2024, 1, 15, 12, 0, 0)
        file_path = find_price_file("BTC_USD", target, tmp_path)
        assert file_path is not None
        # Should prefer exact month match
        assert "2024-01-01" in str(file_path)

    def test_find_price_file_multi_month(self, tmp_path):
        """Test finding multi-month file covering target date."""
        (tmp_path / "BTC_USD-trades-2024-01-01.feather").touch()  # Jan
        (tmp_path / "BTC_USD-trades-2024-02-03.feather").touch()  # Feb-Apr

        # March 15 should match multi-month file starting Feb
        target = datetime(2024, 3, 15, 12, 0, 0)
        file_path = find_price_file("BTC_USD", target, tmp_path)
        assert file_path is not None
        assert "2024-02-03" in str(file_path)  # Feb 2024, 3 months

    def test_find_price_file_fallback(self, tmp_path):
        """Test fallback to closest file."""
        (tmp_path / "BTC_USD-trades-2024-01-01.feather").touch()

        # June date - no exact match, should use Jan file
        target = datetime(2024, 6, 15, 12, 0, 0)
        file_path = find_price_file("BTC_USD", target, tmp_path)
        assert file_path is not None


class TestListAvailable:
    """Test listing available data."""

    def test_list_available_pairs(self, tmp_path):
        """Test listing available pairs."""
        (tmp_path / "BTC_USD-trades-2024-01-01.feather").touch()
        (tmp_path / "ETH_USD-trades-2024-01-01.feather").touch()

        pairs = list_available_pairs(tmp_path)
        assert "BTC_USD" in pairs
        assert "ETH_USD" in pairs

    def test_list_available_date_ranges(self, tmp_path):
        """Test listing available date ranges."""
        (tmp_path / "BTC_USD-trades-2024-01-03.feather").touch()  # Jan-Mar
        (tmp_path / "BTC_USD-trades-2024-04-01.feather").touch()  # Apr

        ranges = list_available_date_ranges(tmp_path, pair="BTC_USD")
        assert len(ranges) == 2
        assert any(r['months'] == 3 for r in ranges)
        assert any(r['months'] == 1 for r in ranges)


class TestValidation:
    """Test validation functions."""

    def test_validate_nonexistent_directory(self, tmp_path):
        """Test validation with non-existent directory."""
        from price_helper.utils import validate_price_directory
        nonexistent = tmp_path / "does_not_exist"
        assert validate_price_directory(nonexistent) is False

    def test_validate_empty_directory(self, tmp_path):
        """Test validation with empty directory."""
        from price_helper.utils import validate_price_directory
        assert validate_price_directory(tmp_path) is False

    def test_validate_valid_directory(self, tmp_path):
        """Test validation with valid directory."""
        from price_helper.utils import validate_price_directory
        # Create a dummy feather file
        (tmp_path / "dummy.feather").touch()
        assert validate_price_directory(tmp_path) is True
