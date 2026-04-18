# API Reference

## Convenience Functions

### get_closest_price()

```python
def get_closest_price(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None
) -> float
```

Get the closest price for a timestamp and pair.

**Parameters:**
- `dt` - Target datetime (naive assumed local, aware converted appropriately)
- `pair` - Trading pair string (e.g., "BTC_USDT")
- `price_dir` - Directory containing `.feather` files
- `delimiter` - Delimiter for parsing pair strings
- `tolerance_seconds` - Maximum allowed difference in seconds

**Returns:** Closest price value

**Raises:** `PriceNotFoundError` if price cannot be found

---

### get_closest_price_with_time()

```python
def get_closest_price_with_time(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None
) -> Tuple[float, datetime]
```

Get the closest price and its timestamp.

**Returns:** Tuple of `(price, timestamp_in_local_tz)`

---

### get_chained_price()

```python
def get_chained_price(
    dt: datetime,
    pair: str,
    price_dir: Union[str, Path] = "~/ollama/claudehome/price",
    delimiter: str = "_",
    tolerance_seconds: Optional[int] = None,
    max_chain_length: int = 4
) -> float
```

Get chained price for cross-rate calculation.

Tries direct price first, then falls back to chain calculation via intermediate currencies.

**Parameters:**
- `max_chain_length` - Maximum number of pairs in chain (default: 4)

**Example:** If EUR_JPY not available, calculates `EUR_USD * USD_JPY`

---

## Classes

### PriceHelper

Main class for price lookups with file caching.

```python
class PriceHelper:
    def __init__(
        self,
        price_dir: Union[str, Path] = "~/ollama/claudehome/price",
        delimiter: str = "_",
        timestamp_col: Optional[str] = None,
        price_col: Optional[str] = None
    )
```

**Parameters:**
- `price_dir` - Directory containing price files
- `delimiter` - Delimiter for pair parsing
- `timestamp_col` - Column name for timestamps (auto-detected if None)
- `price_col` - Column name for prices (auto-detected if None)

**Methods:**

#### get_closest_price(dt, pair, tolerance_seconds=None)
Find closest price for datetime and pair.

#### get_closest_price_with_time(dt, pair, tolerance_seconds=None)
Find closest price and return with actual timestamp.

#### __enter__() / __exit__()
Context manager support for resource cleanup.

---

### ChainResolver

Resolver for calculating chained/cross rates.

```python
class ChainResolver:
    def __init__(
        self,
        price_dir: Union[str, Path] = "~/ollama/claudehome/price",
        delimiter: str = "_",
        max_chain_length: int = 4
    )
```

**Methods:**

#### get_chained_price(dt, pair, tolerance_seconds=None)
Calculate price via chain of available pairs.

#### find_chain(pair, dt=None)
Find a chain of pairs connecting base to quote currency.

---

### PriceNotFoundError

Exception raised when price cannot be found.

```python
try:
    price = get_closest_price(dt, "UNKNOWN_PAIR")
except PriceNotFoundError as e:
    print(f"Error: {e}")
```

---

## Utility Functions

### parse_pair(pair, delimiter="_")
Parse pair string into (base, quote) tuple.

```python
base, quote = parse_pair("BTC_USDT")
# Returns: ("BTC", "USDT")
```

### to_local_timezone(dt)
Convert datetime to local timezone (Australia/Sydney).

### to_utc(dt)
Convert datetime to UTC.

### find_price_file(pair, dt, price_dir, delimiter)
Find price file path for pair and datetime.

### list_available_pairs(price_dir)
List all available trading pairs in directory.

### validate_price_directory(price_dir)
Validate directory exists and contains `.feather` files.
