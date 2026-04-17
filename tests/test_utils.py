"""Tests for utility functions."""
import pytest
from datetime import datetime
from pathlib import Path

from price_helper.utils import (
    parse_pair,
    get_base_symbol,
    get_quote_symbol,
    build_filename_pattern,
    find_price_file,
    list_available_pairs,
    list_available_months,
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


class TestBuildFilenamePattern:
    """Test filename pattern building."""

    def test_build_pattern(self):
        """Test building filename pattern."""
        pattern = build_filename_pattern("BTC", "202401")
        assert pattern == "BTC*202401.feather"


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
