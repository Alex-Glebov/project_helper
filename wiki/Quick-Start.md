# Quick Start

## Basic Usage

### 1. Simple One-Shot Lookup

Use the convenience functions for quick lookups:

```python
from datetime import datetime
from price_helper import get_closest_price

price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USDT"
)

print(f"Price: {price}")
```

### 2. Get Price with Timestamp

When you need to know the exact timestamp of the returned price:

```python
from price_helper import get_closest_price_with_time

price, timestamp = get_closest_price_with_time(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USDT"
)

print(f"Price: {price} at {timestamp}")
```

### 3. Chained Price (Cross-Rates)

When direct pair data is unavailable, automatically calculate via intermediate pairs:

```python
from price_helper import get_chained_price

# If EUR_JPY not available directly, calculates: EUR_USD * USD_JPY
price = get_chained_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="EUR_JPY"
)
```

## Using the Class API

For multiple lookups, use `PriceHelper` with context manager:

```python
from price_helper import PriceHelper

with PriceHelper() as helper:
    # Efficient - files are cached
    price1 = helper.get_closest_price(dt1, "BTC_USDT")
    price2 = helper.get_closest_price(dt2, "BTC_USDT")
    price3 = helper.get_closest_price(dt3, "ETH_USDT")
```

## Tolerance Control

Limit how far from the target time to search:

```python
# Raise PriceNotFoundError if no price within 60 seconds
price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USDT",
    tolerance_seconds=60
)
```

## Error Handling

```python
from price_helper import get_closest_price, PriceNotFoundError

try:
    price = get_closest_price(dt, "UNKNOWN_PAIR")
except PriceNotFoundError as e:
    print(f"Price not found: {e}")
```

## Next Steps

- See [[Examples]] for more detailed patterns
- See [[API Reference]] for complete documentation
- See [[Architecture]] for understanding the design
