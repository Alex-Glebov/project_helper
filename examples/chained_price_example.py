"""
Example: Using ChainResolver for cross-rate calculations

Demonstrates how to calculate prices for pairs that don't have direct data files
by chaining through intermediate currencies.
"""
from datetime import datetime
from price_helper import ChainResolver, get_chained_price, PriceNotFoundError

print("=" * 60)
print("ChainResolver Example: Cross-Rate Calculations")
print("=" * 60)

# Example 1: Direct price lookup (no chain needed)
print("\nExample 1: Direct price (BTC_USDT)")
print("-" * 40)
try:
    price = get_chained_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_USDT"
    )
    print(f"Price: ${price:,.2f} USDT")
except PriceNotFoundError as e:
    print(f"Error: {e}")

# Example 2: Cross-rate calculation via chain
print("\nExample 2: Cross-rate (BTC_ETH via intermediate)")
print("-" * 40)
try:
    # If BTC_ETH not available directly, calculates via USDT:
    # BTC_ETH = BTC_USDT / ETH_USDT
    price = get_chained_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_ETH"
    )
    print(f"Price: {price:.6f} ETH per BTC")
    print("(Calculated via chain: BTC_USDT / ETH_USDT)")
except PriceNotFoundError as e:
    print(f"Error: {e}")

# Example 3: Inverse calculation
print("\nExample 3: Inverse rate (ETH_BTC)")
print("-" * 40)
try:
    price = get_chained_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="ETH_BTC"
    )
    print(f"Price: {price:.6f} BTC per ETH")
except PriceNotFoundError as e:
    print(f"Error: {e}")

# Example 4: Using ChainResolver class for multiple queries
print("\nExample 4: ChainResolver class with multiple queries")
print("-" * 40)

resolver = ChainResolver()
pairs_to_check = ["BTC_USDT", "ETH_USDT", "BTC_ETH", "ETH_BTC"]
dt = datetime(2024, 1, 15, 12, 30)

for pair in pairs_to_check:
    try:
        # Find the chain path
        chain = resolver.find_chain(pair, dt)
        if chain and len(chain) > 1:
            path = " -> ".join(chain)
            print(f"\n{pair}: via chain [{path}]")
        else:
            print(f"\n{pair}: direct lookup")

        # Get the price
        price = resolver.get_chained_price(dt, pair)
        print(f"  Price: {price}")

    except PriceNotFoundError as e:
        print(f"\n{pair}: Not available - {e}")

# Example 5: Custom configuration
print("\nExample 5: Custom delimiter and chain length")
print("-" * 40)

resolver2 = ChainResolver(delimiter="-", max_chain_length=3)
print("Configured with '-' delimiter and max_chain_length=3")
print("(Actual lookup would require files named BTC-USDT-trades-*.feather)")

# Example 6: Error handling
print("\nExample 6: Error handling for unavailable pairs")
print("-" * 40)

try:
    price = get_chained_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="UNKNOWN_PAIR",
        max_chain_length=2
    )
    print(f"Price: {price}")
except PriceNotFoundError as e:
    print(f"Caught expected error: {e}")

print("\n" + "=" * 60)
print("Examples completed!")
print("=" * 60)
