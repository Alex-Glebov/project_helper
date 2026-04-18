# Troubleshooting

## Common Issues

### PriceNotFoundError: No price file found

**Cause:** The price file doesn't exist for the requested pair and date.

**Solution:**
```python
from price_helper import list_available_pairs
from pathlib import Path

# Check available pairs
pairs = list_available_pairs(Path("~/claudehome/price"))
print(pairs)
```

**Check:**
- File naming convention: `{PAIR}-trades-{YYYYMMDD}.feather`
- Date format in filename (YYYYMMDD)
- File location matches `price_dir` parameter

---

### PriceNotFoundError: No price within tolerance

**Cause:** No data point within the specified `tolerance_seconds`.

**Solution:**
```python
# Increase tolerance or remove it
price = get_closest_price(dt, pair, tolerance_seconds=300)  # 5 minutes

# Or no tolerance (find closest)
price = get_closest_price(dt, pair)  # Closest match
```

---

### FileNotFoundError: Price directory does not exist

**Cause:** The default or specified price directory doesn't exist.

**Solution:**
```python
from pathlib import Path

# Create directory if needed
price_dir = Path("~/claudehome/price").expanduser()
price_dir.mkdir(parents=True, exist_ok=True)
```

---

### Column not found errors

**Cause:** Feather file has different column names than expected.

**Solution:**
```python
# Specify custom column names
with PriceHelper(
    timestamp_col="time",    # Default: auto-detect (timestamp, ts, time, datetime)
    price_col="close"        # Default: auto-detect (price, close, value, mid)
) as helper:
    price = helper.get_closest_price(dt, pair)
```

---

### Timezone confusion

**Cause:** Datetime conversion not working as expected.

**Solution:**
```python
from price_helper import to_utc, to_local_timezone
import pytz

# Always use aware datetimes for clarity
dt = datetime(2024, 1, 15, 12, 30, tzinfo=pytz.UTC)
price = get_closest_price(dt, pair)

# Or convert explicitly
local_dt = to_local_timezone(naive_dt)
utc_dt = to_utc(naive_dt)
```

---

### Chain resolution fails

**Cause:** No path found between currencies.

**Solution:**
```python
# Check available pairs first
from price_helper import list_available_pairs
print(list_available_pairs(price_dir))

# Ensure intermediate pairs exist (e.g., for EUR_JPY, need EUR_USD and USD_JPY)

# Increase chain length
price = get_chained_price(dt, pair, max_chain_length=5)
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now run your query to see detailed logs
price = get_closest_price(dt, pair)
```

### Verify File Discovery

```python
from price_helper.utils import find_price_file
from pathlib import Path

file_path = find_price_file(
    pair="BTC_USDT",
    dt=datetime(2024, 1, 15),
    price_dir=Path("~/claudehome/price"),
    delimiter="_"
)
print(f"Found file: {file_path}")
```

### Check File Contents

```python
import pandas as pd

df = pd.read_feather("path/to/file.feather")
print(df.columns)  # Verify expected columns exist
print(df.head())   # Check data format
```

---

## Performance Issues

### Slow repeated lookups

**Problem:** Creating new instance for each lookup.

**Fix:** Use context manager for batch operations:

```python
# Slow - creates instance each time
for dt in dates:
    price = get_closest_price(dt, pair)  # New instance

# Fast - reuses cache
with PriceHelper() as helper:
    for dt in dates:
        price = helper.get_closest_price(dt, pair)  # Cached
```

### Memory usage

**Problem:** Loading too many files into cache.

**Fix:** Create fresh instances periodically:

```python
# Process in batches
for batch in chunks(dates, size=100):
    with PriceHelper() as helper:
        for dt in batch:
            price = helper.get_closest_price(dt, pair)
```

---

## Getting Help

If issues persist:

1. Check [[Examples]] for working patterns
2. Review [[API Reference]] for parameter details
3. Verify your data files match expected format
4. File an issue on GitHub with:
   - Code snippet reproducing the issue
   - Expected vs actual behavior
   - File format/structure
