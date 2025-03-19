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
│   ├── engine.py              # Main backtesting engine
│   ├── options_pricer.py      # Options pricing models
│   ├── volatility.py          # Volatility calculations
│   ├── correlation.py         # Correlation calculations
│   ├── weights.py             # Index weight handling
│   ├── universe.py            # Trading universe definition
│   └── __init__.py            # Package indicator
├── data/                      # Data handling
│   ├── processed/             # Processed data files (.csv)
│   └── datagrab.r             # R script for data acquisition
├── testing/                   # Testing scripts
│   ├── options_test.py        # Tests for options pricing
│   └── options_test.ipynb     # Interactive notebook tests
├── config.json                # Configurable parameters
├── constituents-sp500.csv     # S&P 500 constituent stocks with weights
├── main.py                    # Main script to run the backtest
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
- Dispersion strategy parameters

Important dispersion strategy parameters include:
- `entry_threshold`: Difference between implied and realized correlation that triggers entry (default: 0.05)
- `exit_threshold`: Threshold for exiting positions when correlations converge (default: 0.02)
- `max_position_size`: Maximum portfolio allocation for a trade (default: 0.1 or 10%)

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

### Correlation Calculations

The system calculates both realized and implied correlations:

```python
from backtester.correlation import calculate_realized_correlation, calculate_implied_correlation

# Calculate realized correlation between components
realized_corr = calculate_realized_correlation(
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
)

# Calculate implied correlation between index and components
implied_corr = calculate_implied_correlation(
    "SPY",
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
)
```

### Options Pricing

The system provides two options pricing models with enhanced volatility handling:

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

### Running a Backtest

To run a complete backtest of the dispersion trading strategy:

```bash
python main.py
```

This will:
1. Load configuration from `config.json`
2. Initialize the backtesting engine
3. Run the backtest from start to end date
4. Calculate and display performance metrics
5. Save results and plots to the results directory

#### Backtesting Engine

The engine processes each trading day by:
1. Updating the value of existing positions
2. Checking for expired options and closing those positions
3. Generating trading signals based on correlation dispersion
4. Executing trades based on signals
5. Recording end-of-day portfolio values

#### Trading Signals

The dispersion trading system uses two main types of entry signals:

1. **Standard Dispersion Trade** (when `dispersion > entry_threshold`):
   - Sell index options (collect premium)
   - Buy component options (pay premium)
   - Used when implied correlation is significantly higher than realized correlation

2. **Reverse Dispersion Trade** (when `dispersion < -entry_threshold`):
   - Buy index options (pay premium)
   - Sell component options (collect premium)
   - Used when implied correlation is significantly lower than realized correlation

Positions are exited when:
- The disparity between implied and realized correlation narrows below the exit threshold
- Options reach their expiration date

### Results Analysis

After running a backtest, review the performance metrics and outputs:

```python
from backtester.engine import BacktestEngine
import json

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize and run the backtest
engine = BacktestEngine(config)
results = engine.run()

# Review performance metrics
print(f"Total Return: {results['performance_metrics']['total_return']:.2%}")
print(f"Sharpe Ratio: {results['performance_metrics']['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['performance_metrics']['max_drawdown']:.2%}")

# Plot results
engine.plot_results()
```

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

## Index Weights

The system uses index component weights from `constituents-sp500.csv` for more accurate correlation calculations. The weights are used to:
- Calculate weighted implied volatility of the index
- Properly weight components in correlation calculations
- Generate more accurate dispersion signals

## Known Issues and Limitations

- The system requires VIX data for implied volatility calculations
- Short options positions have theoretically unlimited risk
- Limited transaction cost modeling
- No dividends handling in options pricing

## Contributors

Clancy Hughes, chughe25@villanova.edu
