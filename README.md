# Price Helper

A Python package for retrieving price data from Feather files based on timestamp and trading pair.

## Features

- Load price data from `.feather` files
- Find closest price for a given timestamp
- **Automatic timezone handling** (Australia/Sydney local time ↔ UTC)
- Support for multiple timestamp and price column names (auto-detection)
- Flexible pair parsing with custom delimiters
- Date-based file organization with multi-month files
- Optional tolerance constraints

## Timezone Handling

This package uses **Australia/Sydney** as the local timezone:

- **Input**: Naive datetimes are assumed to be in local timezone (Australia/Sydney)
- **File naming**: File dates are in local timezone (e.g., `2024-01-15` means Jan 15 in Sydney)
- **First record**: Approximately 2pm UTC on the previous day (due to Sydney being UTC+10/11)
- **Output**: All returned datetimes are in local timezone (Australia/Sydney)

## Installation

### From Local Path (for development)

```bash
cd ~/ollama/claudehome/project_helper
pip install -e .
```

### From GitHub

```bash
pip install git+https://github.com/Alex-Glebov/project_helper.git
```

## Usage

### Basic Usage

```python
from datetime import datetime
from price_helper import get_closest_price

# Get price for a specific timestamp (naive datetime assumed local/Sydney)
price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30, 0),
    pair="BTC_USD"
)
print(f"Price: {price}")
```

### Get Price with Timestamp

```python
from datetime import datetime
from price_helper import get_closest_price_with_time

# Returns both price and the actual timestamp (in local timezone)
price, actual_time = get_closest_price_with_time(
    dt=datetime(2024, 1, 15, 12, 30, 0),
    pair="BTC_USD"
)
print(f"Price: {price} at {actual_time}")
```

### Advanced Usage with PriceHelper Class

```python
from datetime import datetime
from price_helper import PriceHelper

# Initialize with custom settings
helper = PriceHelper(
    price_dir="~/ollama/claudehome/price",
    delimiter="_",
    timestamp_col="datetime",  # Optional: auto-detected if not set
    price_col="close"          # Optional: auto-detected if not set
)

# Get closest price
price = helper.get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30, 0),
    pair="BTC_USD",
    tolerance_seconds=300  # Optional: max 5 minutes difference
)

# Get price range
# Result timestamps are in local timezone (Australia/Sydney)
df = helper.get_price_range(
    pair="BTC_USD",
    start_dt=datetime(2024, 1, 15, 0, 0, 0),
    end_dt=datetime(2024, 1, 15, 23, 59, 59)
)
```

### Timezone Conversion Utilities

```python
from datetime import datetime
from price_helper import to_local_timezone, to_utc, LOCAL_TIMEZONE

# Convert naive datetime to local timezone (Sydney)
dt_local = to_local_timezone(datetime(2024, 1, 15, 12, 0, 0))

# Convert to UTC for internal processing
dt_utc = to_utc(datetime(2024, 1, 15, 12, 0, 0))

# Get the timezone object
print(f"Local timezone: {LOCAL_TIMEZONE}")  # Australia/Sydney
```

## File Naming Convention

Price files follow this naming pattern:

```
{pair}-trades-{YYYY-MM-dd}.feather
```

Where:
- `{pair}`: Trading pair (e.g., `BTC_USD`)
- `trades`: Fixed identifier
- `{YYYY-MM-dd}`: Start date in local timezone (Australia/Sydney)
- `dd`: Number of months in the file (e.g., `15` could mean data covers 15 days or it's just part of the date)

Examples:
- `BTC_USD-trades-2024-01-15.feather` - BTC/USD data starting Jan 15, 2024 (Sydney)
- `ETH_USD-trades-2024-02-01.feather` - ETH/USD data starting Feb 1, 2024 (Sydney)

**Note**: The first record in a file starting on `2024-01-15` will actually be around `2024-01-14 14:00 UTC` due to Sydney being UTC+10/11.

## Data Format

Feather files should contain:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` or `datetime` | datetime | Price timestamp (usually in UTC) |
| `price` or `close` | float | Price value |

Auto-detected column names:
- **Timestamp columns:** `timestamp`, `datetime`, `time`, `dt`
- **Price columns:** `price`, `close`, `value`, `last`

## API Reference

### `get_closest_price(dt, pair, **kwargs)`

Convenience function to get the closest price.

**Parameters:**
- `dt` (datetime): Target timestamp (naive assumed local/Sydney, aware converted)
- `pair` (str): Trading pair (e.g., "BTC_USD")
- `price_dir` (str, optional): Price directory path. Default: `~/ollama/claudehome/price`
- `delimiter` (str, optional): Pair delimiter. Default: "_"
- `tolerance_seconds` (int, optional): Maximum allowed time difference

**Returns:**
- `float`: Closest price value

**Raises:**
- `PriceNotFoundError`: If price file not found or no data within tolerance

### `get_closest_price_with_time(dt, pair, **kwargs)`

Get the closest price and its timestamp.

**Returns:**
- `tuple`: (price, timestamp_in_local_timezone)

### `PriceHelper` Class

Main class for price retrieval operations.

**Constructor Parameters:**
- `price_dir` (str/Path): Directory containing .feather files
- `delimiter` (str): Delimiter for parsing pair strings
- `timestamp_col` (str, optional): Column name for timestamps
- `price_col` (str, optional): Column name for prices

**Methods:**
- `get_closest_price(dt, pair, tolerance_seconds=None)`: Get closest price
- `get_price_range(pair, start_dt, end_dt)`: Get price data for time range (returns local timezone datetimes)

### Utility Functions

```python
from price_helper.utils import (
    parse_pair,                # Parse pair string into components
    find_price_file,           # Find price file for pair and datetime
    find_price_files_for_pair, # Find all files for a pair
    to_local_timezone,         # Convert to local timezone
    to_utc,                    # Convert to UTC
    LOCAL_TIMEZONE,            # The local timezone object
)
```

## Configuration

### Default Price Directory

The default price directory is `~/ollama/claudehome/price`. You can override this:

```python
# Method 1: Use helper class
helper = PriceHelper(price_dir="/custom/path/to/prices")

# Method 2: Use convenience function
price = get_closest_price(dt, pair, price_dir="/custom/path")
```

### Logging

Enable logging to see debug information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Error Handling

```python
from price_helper import get_closest_price, PriceNotFoundError
from datetime import datetime

try:
    price = get_closest_price(
        dt=datetime(2024, 1, 15, 12, 30),
        pair="BTC_USD",
        tolerance_seconds=60  # 1 minute tolerance
    )
except PriceNotFoundError as e:
    print(f"Price not found: {e}")
```

## Project Structure

```
project_helper/
├── price_helper/
│   ├── __init__.py      # Package exports
│   ├── core.py          # PriceHelper class and main logic
│   └── utils.py         # Utility functions and timezone handling
├── tests/               # Unit tests
├── setup.py             # Package configuration
└── README.md            # This file
```

## Development

### Running Tests

```bash
cd ~/ollama/claudehome/project_helper
pip install -e ".[dev]"
pytest
```

### Building Package

```bash
python setup.py sdist bdist_wheel
```

## License

MIT License

## Author

Alex Glebov + Claude code
Email: python@iitsp.com.au
