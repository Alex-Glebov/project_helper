# Architecture

## Package Structure

```
price_helper/
├── __init__.py      # Public API exports
├── core.py          # Implementation classes
├── api.py           # Convenience functions
└── utils.py         # Utility functions
```

## Module Responsibilities

### core.py

Contains the main implementation classes:

- **PriceHelper** - Main class for price lookups with caching
- **ChainResolver** - Cross-rate calculation via intermediate pairs
- **PriceNotFoundError** - Exception for missing price data

### api.py

Standalone convenience functions wrapping the classes:

- **get_closest_price()** - Simple price lookup
- **get_closest_price_with_time()** - Price with timestamp
- **get_chained_price()** - Cross-rate calculation

These functions are stateless and create a new instance on each call. Best for one-shot lookups.

### utils.py

Helper functions used throughout the package:

- **parse_pair()** - Parse pair strings
- **find_price_file()** - Locate files by pair/date
- **to_local_timezone()** / **to_utc()** - Timezone conversions

## Design Patterns

### Separation of Concerns

| Layer | Purpose |
|-------|---------|
| api.py | User-facing convenience API |
| core.py | Implementation details |
| utils.py | Shared utilities |

This separation allows:
- API stability even when internals change
- Easy testing of components
- Clear usage patterns (simple vs. advanced)

### Context Manager Pattern

Both `PriceHelper` and `ChainResolver` implement `__enter__`/`__exit__`:

```python
with PriceHelper() as helper:
    # Resources initialized
    price = helper.get_closest_price(dt, pair)
    # Resources cleaned up automatically
```

Benefits:
- Automatic cleanup even with exceptions
- Clear resource lifecycle
- File cache lifetime management

### Caching Strategy

File data is cached at the instance level:

```python
# One instance - cache reused
with PriceHelper() as helper:
    helper.get_closest_price(dt1, "BTC_USDT")  # Loads file
    helper.get_closest_price(dt2, "BTC_USDT")  # Uses cache
```

For stateless function calls, no caching persists between calls.

## Timezone Handling

All datetime handling follows this flow:

1. **Input** - Naive assumed local (Australia/Sydney), aware converted
2. **Internal** - All operations in UTC
3. **Output** - Returned in local timezone

```
User Input → to_utc() → Search → to_local_timezone() → Output
```

## File Discovery

Files are discovered using the pattern:
```
{PAIR}-trades-{YYYYMMDD}.feather
```

Where:
- `PAIR` = trading pair (e.g., "BTC_USDT")
- `YYYYMMDD` = start date (DD typically 01 for monthly files)

The discovery algorithm:
1. Look for exact month match (day=01)
2. Look for multi-month files covering the date
3. Fall back to closest file before target
4. Final fallback to first available file

## Chain Resolution Algorithm

When direct pair data is unavailable:

1. Parse target pair into (base, quote)
2. Search available pairs for potential paths
3. Build graph of currencies connected by available pairs
4. Find shortest path from base to quote (BFS)
5. Calculate price by multiplying rates along path
6. Support inverse rates (e.g., USD_JPY → JPY_USD)

Example: EUR_JPY
```
Path found: EUR_USD → USD_JPY
Calculation: EUR_JPY = EUR_USD * USD_JPY
```

## Error Handling Strategy

- **PriceNotFoundError** - Data unavailable (main exception)
- **ValueError** - Invalid input parameters
- **FileNotFoundError** - Missing data files

Errors are raised immediately, not silently ignored.

## Extensibility Points

To add custom price sources:

1. Subclass `PriceHelper`
2. Override `_load_data()` or `_get_price_or_inverse()`
3. Use your subclass with the same interface

Example:

```python
class CustomPriceHelper(PriceHelper):
    def _load_data(self, file_path):
        # Custom loading logic
        return custom_load(file_path)
```
