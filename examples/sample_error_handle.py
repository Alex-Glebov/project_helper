"""
Example: Error handling with PriceHelper

Demonstrates how to handle PriceNotFoundError and configure
price directory via environment variable.

Created on 2026-04-18
Author: Alex Glebov + Claude Code
"""
import os
from datetime import datetime

from price_helper import PriceHelper, PriceNotFoundError


def main():
    """Main function demonstrating error handling."""
    # Get price folder from environment variable (useful for debugger launch configs)
    price_folder = os.environ.get('PRICEFOLDER')

    if price_folder:
        print(f"Using price folder from environment: {price_folder}")
        helper = PriceHelper(price_dir=price_folder)
    else:
        print("PRICEFOLDER not set, using default path: ~/claudehome/price")
        helper = PriceHelper()

    # Example 1: Successful lookup
    print("\n--- Example 1: BTC_USDT lookup ---")
    try:
        price = helper.get_closest_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_USDT",
            tolerance_seconds=60  # 1 minute tolerance
        )
        print(f"Price found: {price}")
    except PriceNotFoundError as e:
        print(f"Price not found: {e}")

    # Example 2: Lookup that may fail
    print("\n--- Example 2: BTC_USD lookup (may not exist) ---")
    try:
        price = helper.get_closest_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="BTC_USD",
            tolerance_seconds=60
        )
        print(f"Price found: {price}")
    except PriceNotFoundError as e:
        print(f"Price not found: {e}")

    # Example 3: Lookup with no tolerance (finds closest)
    print("\n--- Example 3: ETH_USDT lookup (no tolerance) ---")
    try:
        price = helper.get_closest_price(
            dt=datetime(2024, 1, 15, 12, 30),
            pair="ETH_USDT"
            # No tolerance - finds closest regardless of time difference
        )
        print(f"Price found: {price}")
    except PriceNotFoundError as e:
        print(f"Price not found: {e}")


if __name__ == "__main__":
    main()
