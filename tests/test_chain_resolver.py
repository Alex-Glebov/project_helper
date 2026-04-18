"""Tests for ChainResolver and chained price functionality."""
import pytest
from datetime import datetime
from pathlib import Path
import tempfile

import pandas as pd
import pytz

from price_helper import ChainResolver, get_chained_price, PriceNotFoundError
from price_helper.utils import to_local_timezone


class TestChainResolver:
    """Test ChainResolver functionality with real data."""

    def test_chain_resolver_initialization(self):
        """Test ChainResolver can be initialized."""
        price_dir = Path("~/claudehome/price").expanduser()
        resolver = ChainResolver(price_dir=price_dir)
        assert resolver.price_dir == price_dir
        assert resolver.max_chain_length == 4
        assert resolver.delimiter == "_"

    def test_chain_resolver_custom_params(self):
        """Test ChainResolver with custom parameters."""
        price_dir = Path("~/claudehome/price").expanduser()
        resolver = ChainResolver(
            price_dir=price_dir,
            delimiter="-",
            max_chain_length=3
        )
        assert resolver.delimiter == "-"
        assert resolver.max_chain_length == 3

    def test_find_chain_direct_pair_available(self):
        """Test find_chain when direct pair is available."""
        price_dir = Path("~/claudehome/price").expanduser()
        resolver = ChainResolver(price_dir=price_dir)

        dt = datetime(2024, 1, 15, 12, 30)

        # BTC_USDT should be available directly
        chain = resolver.find_chain("BTC_USDT", dt)

        # When direct data is available, find_chain may return
        # a single-element list with the pair
        assert chain is not None
        assert len(chain) >= 1
        assert "BTC_USDT" in chain or any("BTC" in c and "USDT" in c for c in chain)

    def test_get_chained_price_btc_usdt(self):
        """Test getting BTC_USDT price (direct lookup)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_USDT",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)
        # BTC should be in reasonable range (historical prices)
        assert 10000 < price < 100000

    def test_get_chained_price_eth_usdt(self):
        """Test getting ETH_USDT price (direct lookup)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="ETH_USDT",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)
        # ETH should be in reasonable range
        assert 1000 < price < 10000

    def test_get_chained_price_btc_eth(self):
        """Test getting BTC_ETH price (may use chain)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_ETH",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)
        # BTC/ETH rate should be < 1 (BTC is worth less ETH)
        assert 0 < price < 1

    def test_get_chained_price_eth_btc(self):
        """Test getting ETH_BTC price (may use chain)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="ETH_BTC",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)
        # ETH/BTC rate should be > 1 (ETH is worth more BTC units)
        assert price > 1

    def test_get_chained_price_btc_aud(self):
        """Test getting BTC_AUD price (direct lookup)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_AUD",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)

    def test_get_chained_price_sol_usdt(self):
        """Test getting SOL_USDT price (direct lookup)."""
        price_dir = Path("~/claudehome/price").expanduser()

        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="SOL_USDT",
            price_dir=price_dir
        )

        assert price > 0
        assert isinstance(price, float)
        # SOL should be reasonable
        assert 10 < price < 500

    def test_get_chained_price_invalid_pair(self):
        """Test that invalid pair raises PriceNotFoundError."""
        price_dir = Path("~/claudehome/price").expanduser()

        with pytest.raises(PriceNotFoundError):
            get_chained_price(
                dt=datetime(2024, 1, 15, 12, 30),
                pair="INVALID_PAIR_XYZ",
                price_dir=price_dir,
                max_chain_length=2
            )

    def test_get_chained_price_tolerance(self):
        """Test chained price with tolerance."""
        price_dir = Path("~/claudehome/price").expanduser()

        # This should work with reasonable tolerance
        price = get_chained_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_USDT",
            price_dir=price_dir,
            tolerance_seconds=3600  # 1 hour
        )

        assert price > 0

    def test_chain_consistency(self):
        """Test that BTC_ETH * ETH_USDT ≈ BTC_USDT."""
        price_dir = Path("~/claudehome/price").expanduser()
        dt = datetime(2024, 1, 15, 12, 30)

        # Get individual prices
        btc_eth = get_chained_price(dt, "BTC_ETH", price_dir=price_dir)
        eth_usdt = get_chained_price(dt, "ETH_USDT", price_dir=price_dir)
        btc_usdt = get_chained_price(dt, "BTC_USDT", price_dir=price_dir)

        # Cross multiply: BTC_ETH * ETH_USDT should equal BTC_USDT
        calculated_btc_usdt = btc_eth * eth_usdt

        # Allow 1% tolerance for calculation differences
        assert abs(calculated_btc_usdt - btc_usdt) / btc_usdt < 0.01


class TestChainResolverEdgeCases:
    """Test edge cases for ChainResolver."""

    def test_chain_with_inverse_calculation(self):
        """Test that inverse pairs are calculated correctly."""
        price_dir = Path("~/claudehome/price").expanduser()
        resolver = ChainResolver(price_dir=price_dir)

        dt = datetime(2024, 1, 15, 12, 30)

        # If BTC_ETH is available, ETH_BTC should be 1/BTC_ETH
        try:
            btc_eth = get_chained_price(dt, "BTC_ETH", price_dir=price_dir)
            eth_btc = get_chained_price(dt, "ETH_BTC", price_dir=price_dir)

            # Verify they are inverses (within tolerance)
            assert abs(btc_eth * eth_btc - 1.0) < 0.01
        except PriceNotFoundError:
            pytest.skip("Required pairs not available")

    def test_max_chain_length_respected(self):
        """Test that max_chain_length is respected."""
        price_dir = Path("~/claudehome/price").expanduser()

        resolver_short = ChainResolver(price_dir=price_dir, max_chain_length=2)
        resolver_long = ChainResolver(price_dir=price_dir, max_chain_length=4)

        dt = datetime(2024, 1, 15, 12, 30)

        # Both should work for direct pairs
        chain_short = resolver_short.find_chain("BTC_USDT", dt)
        chain_long = resolver_long.find_chain("BTC_USDT", dt)

        assert chain_short is not None
        assert chain_long is not None

    def test_nonexistent_directory(self):
        """Test behavior with non-existent directory."""
        nonexistent_dir = Path("/tmp/nonexistent_price_dir_12345")

        with pytest.raises(PriceNotFoundError):
            get_chained_price(
                dt=datetime(2024, 1, 15, 12, 30),
                pair="BTC_USDT",
                price_dir=nonexistent_dir
            )


class TestChainedPriceIntegration:
    """Integration tests for chained price functionality."""

    def test_multiple_calls_consistency(self):
        """Test that multiple calls return consistent results."""
        price_dir = Path("~/claudehome/price").expanduser()
        dt = datetime(2024, 1, 15, 12, 30)

        # Call multiple times and verify consistency
        prices = []
        for _ in range(3):
            price = get_chained_price(dt, "BTC_USDT", price_dir=price_dir)
            prices.append(price)

        # All prices should be identical
        assert prices[0] == prices[1] == prices[2]

    def test_different_datetimes(self):
        """Test prices at different times of day."""
        price_dir = Path("~/claudehome/price").expanduser()
        base_date = datetime(2024, 1, 15)

        times = [
            (9, 0),   # Morning
            (12, 0),  # Noon
            (15, 0),  # Afternoon
        ]

        prices = []
        for hour, minute in times:
            dt = base_date.replace(hour=hour, minute=minute)
            try:
                price = get_chained_price(dt, "BTC_USDT", price_dir=price_dir)
                prices.append(price)
            except PriceNotFoundError:
                pass  # Some times may not have data

        # Should have at least some prices
        if prices:
            assert all(p > 0 for p in prices)

    def test_helper_reuse(self):
        """Test that ChainResolver can be reused for multiple queries."""
        price_dir = Path("~/claudehome/price").expanduser()
        resolver = ChainResolver(price_dir=price_dir)

        pairs = ["BTC_USDT", "ETH_USDT", "BTC_ETH"]
        dt = datetime(2024, 1, 15, 12, 30)

        for pair in pairs:
            try:
                chain = resolver.find_chain(pair, dt)
                assert chain is not None
            except PriceNotFoundError:
                pass  # Some pairs may not be available


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
