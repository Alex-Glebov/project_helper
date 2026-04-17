# Price Helper

A Python package for retrieving price data from Feather files based on timestamp and trading pair.

## Features

- Load price data from `.feather` files
- Find closest price for a given timestamp
- Support for multiple timestamp and price column names (auto-detection)
- Flexible pair parsing with custom delimiters
- Month-based file organization
- Optional tolerance constraints

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

# Get price for a specific timestamp
price = get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30, 0),
    pair="BTC_USD"
)
print(f"Price: {price}")
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
df = helper.get_price_range(
    pair="BTC_USD",
    start_dt=datetime(2024, 1, 15, 0, 0, 0),
    end_dt=datetime(2024, 1, 15, 23, 59, 59)
)
```

## File Naming Convention

Price files should follow this naming pattern:

```
{pair}_{YYYYMM}.feather
```

Examples:
- `BTC_USD_202401.feather` - BTC/USD data for January 2024
- `ETH_USD_202402.feather` - ETH/USD data for February 2024
- `BTC_202401.feather` - BTC data (single symbol) for January 2024

The package searches for files matching the base symbol and year-month of the requested timestamp.

## Data Format

Feather files should contain:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` or `datetime` | datetime | Price timestamp |
| `price` or `close` | float | Price value |

Auto-detected column names:
- **Timestamp columns:** `timestamp`, `datetime`, `time`, `dt`
- **Price columns:** `price`, `close`, `value`, `last`

## API Reference

### `get_closest_price(dt, pair, **kwargs)`

Convenience function to get the closest price.

**Parameters:**
- `dt` (datetime): Target timestamp
- `pair` (str): Trading pair (e.g., "BTC_USD")
- `price_dir` (str, optional): Price directory path. Default: `~/ollama/claudehome/price`
- `delimiter` (str, optional): Pair delimiter. Default: "_"
- `tolerance_seconds` (int, optional): Maximum allowed time difference

**Returns:**
- `float`: Closest price value

**Raises:**
- `PriceNotFoundError`: If price file not found or no data within tolerance

### `PriceHelper` Class

Main class for price retrieval operations.

**Constructor Parameters:**
- `price_dir` (str/Path): Directory containing .feather files
- `delimiter` (str): Delimiter for parsing pair strings
- `timestamp_col` (str, optional): Column name for timestamps
- `price_col` (str, optional): Column name for prices

**Methods:**
- `get_closest_price(dt, pair, tolerance_seconds=None)`: Get closest price
- `get_price_range(pair, start_dt, end_dt)`: Get price data for time range

### Utility Functions

```python
from price_helper.utils import (
    parse_pair,           # Parse pair string into components
    find_price_file,      # Find price file for pair and datetime
    list_available_pairs, # List all available pairs
    list_available_months # List available months for a pair
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
│   └── utils.py         # Utility functions
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
