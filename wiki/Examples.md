# Examples

## Basic Examples

### Example 1: Simple Price Lookup

```python
from datetime import datetime
from price_helper import get_closest_price

price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USDT"
)
print(f"BTC/USDT Price: {price}")
```

### Example 2: Using Context Manager

```python
from price_helper import PriceHelper

# Efficient for multiple lookups - files cached
with PriceHelper() as helper:
    btc_price = helper.get_closest_price(
        datetime(2024, 1, 15, 10, 0), "BTC_USDT"
    )
    eth_price = helper.get_closest_price(
        datetime(2024, 1, 15, 10, 0), "ETH_USDT"
    )
```

### Example 3: Error Handling

```python
from price_helper import get_closest_price, PriceNotFoundError

try:
    price = get_closest_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="UNKNOWN_PAIR",
        tolerance_seconds=60
    )
except PriceNotFoundError as e:
    print(f"Price not found: {e}")
```

## Advanced Examples

### Example 4: Cross-Rate Calculation

When EUR_JPY data is not available directly:

```python
from price_helper import get_chained_price, ChainResolver

# Simple API
price = get_chained_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="EUR_JPY"
)
# Calculates: EUR_USD * USD_JPY

# Class API - for more control
with ChainResolver(max_chain_length=3) as resolver:
    price = resolver.get_chained_price(
        datetime(2024, 1, 15, 12, 30),
        "BTC_ETH"  # Calculates via USD
    )
```

### Example 5: Price with Exact Timestamp

```python
from price_helper import get_closest_price_with_time

price, actual_timestamp = get_closest_price_with_time(
    dt=datetime(2024, 1, 15, 12, 30, 0),
    pair="BTC_USDT"
)

print(f"Requested: 2024-01-15 12:30:00")
print(f"Found: {actual_timestamp} (price: {price})")
```

### Example 6: Custom Price Directory

```python
from pathlib import Path
from price_helper import PriceHelper

custom_dir = Path("/path/to/my/prices")

with PriceHelper(price_dir=custom_dir) as helper:
    price = helper.get_closest_price(
        datetime(2024, 1, 15, 12, 30),
        "BTC_USDT"
    )
```

### Example 7: Custom Column Names

If your feather files use different column names:

```python
with PriceHelper(
    price_dir="~/claudehome/price",
    timestamp_col="time",      # Default: auto-detect
    price_col="close"          # Default: auto-detect
) as helper:
    price = helper.get_closest_price(dt, "BTC_USDT")
```

### Example 8: Timezone Handling

```python
from datetime import datetime
import pytz
from price_helper import get_closest_price

# Naive datetime (assumed local timezone - Australia/Sydney)
dt_naive = datetime(2024, 1, 15, 12, 30)
price = get_closest_price(dt_naive, "BTC_USDT")

# Timezone-aware datetime (auto-converted)
dt_utc = datetime(2024, 1, 15, 12, 30, tzinfo=pytz.UTC)
price = get_closest_price(dt_utc, "BTC_USDT")
```

### Example 9: Batch Processing

```python
from price_helper import PriceHelper
from datetime import datetime, timedelta

pairs = ["BTC_USDT", "ETH_USDT", "SOL_USDT"]
dates = [datetime(2024, 1, 15) + timedelta(hours=i) for i in range(24)]

results = []
with PriceHelper() as helper:
    for pair in pairs:
        for dt in dates:
            try:
                price = helper.get_closest_price(dt, pair)
                results.append({
                    'pair': pair,
                    'datetime': dt,
                    'price': price
                })
            except PriceNotFoundError:
                pass
```

### Example 10: Listing Available Data

```python
from price_helper import list_available_pairs, list_available_date_ranges
from pathlib import Path

price_dir = Path("~/claudehome/price").expanduser()

# List all pairs
pairs = list_available_pairs(price_dir)
print(f"Available pairs: {pairs}")

# List date ranges for a specific pair
ranges = list_available_date_ranges(price_dir, pair="BTC_USDT")
for r in ranges:
    print(f"{r['start']} - {r['end']}: {r['months']} month(s)")
```

## Common Patterns

### Pattern: Fallback Chain

```python
def get_price_with_fallback(dt, pair):
    """Try direct price, then chained price."""
    from price_helper import get_closest_price, get_chained_price
    
    try:
        return get_closest_price(dt, pair)
    except PriceNotFoundError:
        return get_chained_price(dt, pair)
```

### Pattern: Validate Before Query

```python
def validate_and_get(dt, pair):
    from price_helper import validate_price_directory, get_closest_price
    from pathlib import Path
    
    price_dir = Path("~/claudehome/price")
    if not validate_price_directory(price_dir):
        raise ValueError("Invalid price directory")
    
    return get_closest_price(dt, pair)
```
