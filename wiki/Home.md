# Price Helper

A Python package for retrieving historical price data from Feather files.

## Overview

Price Helper provides utilities to fetch the closest price data for a given timestamp and trading pair from `.feather` files. It supports:

- **Direct price lookup** - Find the closest price for any trading pair
- **Chain resolution** - Calculate cross-rates when direct pair data is unavailable
- **Timezone handling** - Automatic conversion between local (Australia/Sydney) and UTC
- **File caching** - Efficient caching for repeated lookups
- **Context manager support** - Clean resource management

## Quick Example

```python
from datetime import datetime
from price_helper import get_closest_price, PriceHelper

# Simple API - one-shot lookup
price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USDT"
)

# Class-based API - efficient for multiple lookups
with PriceHelper() as helper:
    price1 = helper.get_closest_price(datetime(2024, 1, 15, 10, 0), "BTC_USDT")
    price2 = helper.get_closest_price(datetime(2024, 1, 15, 11, 0), "BTC_USDT")
```

## Navigation

- [[Installation]] - Setup and installation instructions
- [[Quick Start]] - Get up and running quickly
- [[API Reference]] - Complete API documentation
- [[Examples]] - Usage examples and patterns
- [[Architecture]] - Package structure and design
- [[Troubleshooting]] - Common issues and solutions

## File Naming Convention

Price files should follow the pattern:
```
{PAIR}-trades-{YYYYMMDD}.feather
```

Example: `BTC_USDT-trades-20240101.feather`

The date portion indicates the start of the month covered by the file.

## License

MIT License - See repository for details.
