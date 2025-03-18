# Dispersion Trading System

A quantitative trading system for implementing dispersion trading strategies using options. This system includes data fetching, options pricing, and backtesting capabilities.

## Project Overview

Dispersion trading is a volatility trading strategy that involves:
1. Selling index options
2. Buying options on individual components of the index
3. Profiting from the spread between implied correlation and realized correlation

This codebase provides the tools to analyze, backtest, and potentially implement dispersion trading strategies.

## Project Structure
dispersion-trading/
├── backtester/ # Backtesting framework
│ ├── options_pricer.py # Options pricing models
│ ├── options_test.py # Tests for options pricing
│ └── universe.py # Trading universe definition
├── data/ # Data handling
│ ├── processed/ # Processed data files (.csv)
│ └── datagrab.r # R script for data acquisition
├── constituents-sp500.csv # S&P 500 constituent stocks
└── README.md # This file
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

### Data Acquisition

Use the R script to download historical price data:

```bash
Rscript data/datagrab.r SPY,AAPL,MSFT 2020-01-01 2024-12-31
```

This will download data for the specified symbols (SPY, AAPL, MSFT) from 2020-01-01 to 2024-12-31 and save it to `data/processed/`.

### Options Pricing

The system provides two options pricing models:

1. Black-Scholes (for European options)
2. Binomial Tree (for American options with early exercise)

Example usage:

```python
from backtester.options_pricer import price_options

# Price a call option
option_price = price_options(
    ticker="SPY",
    current_date="2022-01-10",
    expiration_date="2022-02-17",
    strike_price=450,
    option_type="call",
    model="black_scholes"
)

print(f"Option price: ${option_price:.2f}")
```

### Trading Universe

The `universe.py` script handles:
- Loading S&P 500 constituents
- Selecting a subset of tickers
- Fetching historical data for analysis

You can modify the selection criteria in this file to change your trading universe.

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

Note that the options pricer expects data files to be in the `data/processed/` directory relative to the current working directory. If you're running scripts from a subdirectory, you may need to adjust paths accordingly.

## Contributors

Clancy Hughes, chughe25@villanova.edu