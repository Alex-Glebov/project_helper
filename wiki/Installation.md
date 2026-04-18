# Installation

## Requirements

- Python 3.8+
- pandas
- pyarrow (for Feather support)
- pytz

## Install from Source

```bash
git clone https://github.com/Alex-Glebov/project_helper.git
cd project_helper
pip install -e .
```

## Dependencies

The package requires:

```
pandas>=1.0.0
pyarrow>=3.0.0
pytz
```

Install dependencies manually:
```bash
pip install pandas pyarrow pytz
```

## Verify Installation

```python
from price_helper import PriceHelper, get_closest_price
print("Installation successful!")
```

## Development Setup

For development with tests:

```bash
pip install -e ".[dev]"
pytest tests/
```

## Directory Structure

Ensure your price data directory exists:

```bash
mkdir -p ~/ollama/claudehome/price
```

Place your `.feather` files in this directory following the naming convention:
```
{PAIR}-trades-{YYYYMMDD}.feather
```

Example:
```
~/ollama/claudehome/price/
├── BTC_USDT-trades-20240101.feather
├── ETH_USDT-trades-20240101.feather
└── EUR_USD-trades-20240101.feather
```
