# Dispersion Trading System

A quantitative trading system for implementing dispersion trading strategies using options. This system includes data fetching, options pricing, and backtesting capabilities.

## Project Overview

Dispersion trading is a volatility trading strategy that involves:
1. Selling index options
2. Buying options on individual components of the index
3. Profiting from the spread between implied correlation and realized correlation

This codebase provides the tools to analyze, backtest, and potentially implement dispersion trading strategies.

## Project Structure

```
dispersion-trading/
├── backtester/                # Backtesting framework
│   ├── options_pricer.py      # Options pricing models
│   ├── volatility.py          # Volatility and correlation calculations
│   ├── universe.py            # Trading universe definition
│   └── __init__.py            # Package indicator
├── data/                      # Data handling
│   ├── processed/             # Processed data files (.csv)
│   └── datagrab.r             # R script for data acquisition
├── testing/                   # Testing scripts
│   ├── options_test.py        # Tests for options pricing
│   └── options_test.ipynb     # Interactive notebook tests
├── config.json                # Configurable parameters
├── constituents-sp500.csv     # S&P 500 constituent stocks
└── README.md                  # This file
```

## Dependencies

### Python Dependencies
- numpy
- pandas
- scipy
- matplotlib (for visualization)

### R Dependencies
- quantmod
- xts
- zoo

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dispersion-trading.git
cd dispersion-trading
```

2. Install Python dependencies:
```bash
pip install numpy pandas scipy matplotlib
```

3. Install R dependencies:
```R
install.packages(c("quantmod", "xts", "zoo"))
```

## Usage

### Configuration

The system uses a central `config.json` file for all parameters. You can customize:
- Backtest date ranges
- Universe selection criteria
- Trading parameters
- Options pricing models
- Volatility calculation methods

### Data Acquisition

Use the R script to download historical price data:

```bash
Rscript data/datagrab.r SPY,^VIX,AAPL,MSFT 2020-01-01 2024-12-31
```

This will download data for the specified symbols from 2020-01-01 to 2024-12-31 and save it to `data/processed/`. Note that including `^VIX` is necessary for implied volatility calculations.

### Universe Selection

The `universe.py` script handles:
- Loading S&P 500 constituents
- Selecting a subset of tickers based on criteria in config.json
- Fetching historical data for the index, VIX, and selected stocks

```python
# Example from Python
from backtester.universe import grab_data

# Download data for specific tickers
grab_data("SPY,^VIX,AAPL", "2020-01-01", "2024-12-31")
```

### Volatility Calculations

The system supports multiple volatility calculation methods:

```python
from backtester.volatility import calculate_historical_volatility, calculate_vix_implied_volatility

# Calculate historical volatility
hist_vol = calculate_historical_volatility("AAPL", "2022-01-10", lookback=30)

# Calculate VIX-scaled implied volatility
implied_vol = calculate_vix_implied_volatility("AAPL", "2022-01-10", lookback=30)
```

### Options Pricing

The system provides two options pricing models with enhanced volatility handling:

1. Black-Scholes (for European options)
2. Binomial Tree (for American options with early exercise)

```python
from backtester.options_pricer import price_options

# Price a call option using VIX-implied volatility
option_price = price_options(
    ticker="SPY",
    current_date="2022-01-10",
    expiration_date="2022-02-17",
    strike_price=450,
    option_type="call",
    model="black_scholes",
    volatility_method="vix_implied"  # Use VIX-scaled implied volatility
)

# Or use custom volatility
custom_price = price_options(
    ticker="SPY",
    current_date="2022-01-10",
    expiration_date="2022-02-17",
    strike_price=450,
    option_type="call",
    volatility_method="custom",
    volatility_value=0.25  # 25% annualized volatility
)

print(f"Option price: ${option_price:.2f}")
```

## Volatility and Correlation Models

### Volatility Calculation Methods

The system supports multiple approaches to volatility estimation:

1. **Historical Volatility**: Calculated from historical returns over a specified lookback period
2. **VIX-Implied Volatility**: Scales historical volatility using the VIX as a proxy for market volatility risk premium
3. **Custom Volatility**: User-specified volatility values

### Implied Correlation

Implied correlation is calculated using implied volatilities of the index and its components:

1. The system calculates implied volatilities for both index and components
2. It uses these values to derive the implied correlation embedded in options prices
3. This forms the basis of dispersion trading signals

## Options Pricing Models

### Black-Scholes Model

Used for pricing European options (options that can only be exercised at expiration).

Key assumptions:
- Log-normal distribution of stock prices
- Constant volatility
- No dividends
- No early exercise

### Binomial Tree Model

Used for pricing American options (options that can be exercised before expiration).

Advantages:
- Handles early exercise
- More flexible than Black-Scholes
- Can incorporate dividends

## Data Structure

The historical price data is stored in CSV format with the following columns:
- date: Trading date
- Open: Opening price
- High: High price for the day
- Low: Low price for the day
- Close: Closing price
- Volume: Trading volume
- Adjusted: Adjusted closing price (adjusted for splits and dividends)

## Path Configuration

Note that the options pricer expects data files to be in the `data/processed/` directory relative to the project root. When running from subdirectories, ensure proper path configuration or run from the project root.

## Future Development

Planned enhancements include:
- Correlation calculation module
- Full backtesting engine
- Portfolio optimization
- Performance visualization

## Contributors

Clancy Hughes, chughe25@villanova.edu
