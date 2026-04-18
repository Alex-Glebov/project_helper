"""
Example: Using PriceHelper with 'with' statement (context manager)

The 'with' statement ensures proper setup and cleanup, even if errors occur.
"""
from datetime import datetime
from price_helper import PriceHelper, PriceNotFoundError

# Example 1: Basic usage with 'with'
print("=" * 60)
print("Example 1: Basic 'with' usage")
print("=" * 60)

with PriceHelper(price_dir="~/claudehome/price") as helper:
    # helper is automatically cleaned up after this block
    price = helper.get_closest_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_USDT"
    )
    print(f"Price: {price}")

# Example 2: Multiple operations in one context
print("\n" + "=" * 60)
print("Example 2: Multiple operations")
print("=" * 60)

with PriceHelper(price_dir="~/claudehome/price") as helper:
    # Get multiple prices efficiently (files cached during context)
    price1 = helper.get_closest_price(
        dt=datetime(2024, 1, 15, 10, 0),
        pair="BTC_USDT"
    )
    price2 = helper.get_closest_price(
        dt=datetime(2024, 1, 15, 11, 0),
        pair="BTC_USDT"
    )
    price3 = helper.get_closest_price(
        dt=datetime(2024, 1, 15, 12, 0),
        pair="ETH_USDT"
    )
    print(f"BTC at 10:00: {price1}")
    print(f"BTC at 11:00: {price2}")
    print(f"ETH at 12:00: {price3}")

# Example 3: Error handling with 'with'
print("\n" + "=" * 60)
print("Example 3: Error handling")
print("=" * 60)

try:
    with PriceHelper(price_dir="~/claudehome/price") as helper:
        # This might raise PriceNotFoundError
        price = helper.get_closest_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="UNKNOWN_PAIR",
            tolerance_seconds=60
        )
        print(f"Price: {price}")
except PriceNotFoundError as e:
    print(f"Error caught: {e}")
    # Context manager still cleaned up properly!

# Example 4: Custom configuration
print("\n" + "=" * 60)
print("Example 4: Custom configuration")
print("=" * 60)

with PriceHelper(
    price_dir="~/claudehome/price",
    delimiter="_",
    timestamp_col="time",
    price_col="close"
) as helper:
    price = helper.get_closest_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_USDT"
    )
    print(f"Price (using 'close' column): {price}")

# Example 5: Using with ChainResolver
print("\n" + "=" * 60)
print("Example 5: ChainResolver with 'with'")
print("=" * 60)

from price_helper import ChainResolver

with ChainResolver(price_dir="~/claudehome/price") as resolver:
    # Get chained price (cross-rate calculation)
    price = resolver.get_chained_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_ETH"  # If no direct file, calculates via USD
    )
    print(f"Chained price: {price}")

print("\n" + "=" * 60)
print("All examples completed!")
print("=" * 60)
