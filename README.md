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
│   ├── dspx.py                # DSPX index and signal calculations
│   ├── risk_manager.py        # Risk management logic
│   ├── logger.py              # Logging utility
│   ├── weights.py             # Index weight handling
│   ├── universe.py            # Trading universe definition (auxiliary)
│   └── __init__.py            # Package indicator
├── data/                      # Data handling
│   ├── processed/             # Processed data files (.csv)
│   └── datagrab.r             # R script for data acquisition
├── results/                   # Backtest results (CSV reports, plots, summary)
├── performance/               # Performance related outputs (e.g., tear sheets - if generated)
├── testing/                   # Testing scripts
│   ├── options_test.py        # Tests for options pricing
│   └── options_test.ipynb     # Interactive notebook tests
├── config.json                # Configurable parameters for the backtest
├── constituents-sp500.csv     # S&P 500 constituent stocks with weights
├── DSPX_History.csv           # Historical CBOE S&P 500 Dispersion Index data
├── main.py                    # Main script to run the backtest
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── README_RISK_MANAGEMENT.md  # Detailed guide on risk management features
├── methodology-cboe-sp-500-dispersion-index.pdf # CBOE DSPX methodology
└── weights-sp500.csv          # (Potentially alternative or historical S&P 500 weights file)
```

## Dependencies

### Python Dependencies
- numpy
- pandas
- scipy
- matplotlib

(See `requirements.txt` for specific versions. It is recommended to update `requirements.txt` if these are not listed.)

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
# It's recommended to use the requirements file:
# pip install -r requirements.txt 
# (Ensure requirements.txt is up-to-date with pandas and scipy)
```

3. Install R dependencies:
```R
install.packages(c("quantmod", "xts", "zoo"))
```

## Usage

### Configuration

The system uses a central `config.json` file for all parameters. You can customize:
- Backtest date ranges (`backtest` section: `start_date`, `end_date`)
- Portfolio settings (`portfolio` section: `initial_cash`, `leverage_limit`, `benchmark`)
- Universe selection criteria (`universe` section: `index`, `num_stocks`, `random_selection`, `seed`)
- Trading parameters (`trading` section: `commission`, `slippage`, `market_impact`)
- Options pricing models and parameters (`options` section: `pricing_model`, `risk_free_rate`, `volatility_method`, etc.)
- Volatility calculation methods (via `options` section and `volatility.py`)
- Dispersion strategy parameters (`dispersion` section)
- Risk management rules (`risk_management` section)
- Logging verbosity and output (`logging` section)
- Data and results paths (`paths` section)

Key dispersion strategy parameters in `config.json` include:
- `entry_threshold`: Difference between implied and realized correlation (or DSPX signal) that triggers entry (e.g., default in sample config: 2.0)
- `exit_threshold`: Threshold for exiting positions when correlations converge (e.g., default in sample config: 1.5)
- `max_position_size`: Maximum portfolio allocation for a single dispersion trade (e.g., default in sample config: 0.02 or 2%)
- `dspx_lookback`: Lookback period for DSPX calculations.

The `risk_management` section in `config.json` allows for detailed control over risk, including:
- `max_portfolio_risk_pct`, `max_position_risk_pct`
- `stop_loss_pct`, `max_drawdown_pct`
- `position_sizing_method` (e.g., 'kelly')
- Vega and Theta limits for options exposure
For more details, see `README_RISK_MANAGEMENT.md`.

The `logging` section controls console output, debug mode, and whether to save trades/positions history.

### Data Acquisition

Use the R script to download historical price data:

```bash
Rscript data/datagrab.r SPY,^VIX,AAPL,MSFT 2020-01-01 2024-12-31
```

This will download data for the specified symbols from 2020-01-01 to 2024-12-31 and save it to `data/processed/` (as configured in `config.json`). Note that including `^VIX` is necessary for VIX-based implied volatility calculations. Historical `DSPX_History.csv` data should also be present for strategies utilizing it.

### Universe Selection

The `BacktestEngine` handles loading data for the index (e.g., SPY), VIX, and selected component stocks based on the `universe` section in `config.json`. It can randomly select from `constituents-sp500.csv` or use a predefined list. The data is sourced from the directory specified in `paths.data_dir` in `config.json`.

The `universe.py` script contains auxiliary functions but is not the primary data loading mechanism for the engine.

### Volatility Calculations

The system supports multiple volatility calculation methods, primarily configured via the `options.volatility_method` in `config.json` for option pricing. Key functions in `backtester.volatility.py`:

```python
from backtester.volatility import calculate_historical_volatility, calculate_vix_implied_volatility, calculate_implied_volatilities

# Calculate historical volatility (used internally or for custom analysis)
hist_vol = calculate_historical_volatility("AAPL", "2022-01-10", lookback=30)

# Calculate VIX-scaled implied volatility for a single ticker (used internally or for custom analysis)
# This method uses VIX data to adjust historical volatility.
implied_vol_single = calculate_vix_implied_volatility("AAPL", "2022-01-10", lookback=30)

# Calculate VIX-scaled implied volatilities for the index and its components (used by correlation module)
implied_vols_dict = calculate_implied_volatilities("SPY", ["AAPL", "MSFT"], "2022-01-10", lookback=30)
```

### Correlation Calculations

The system calculates correlation dispersion, which is key for generating trading signals. The main function used by the `BacktestEngine` is `calculate_correlation_dispersion` from `backtester.correlation.py`.

```python
from backtester.correlation import calculate_realized_correlation, calculate_average_realized_correlation, calculate_implied_correlation, calculate_correlation_dispersion

# Calculate realized correlation matrix between components (auxiliary)
realized_corr_matrix = calculate_realized_correlation(
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
)

# Calculate average realized correlation (used within dispersion calculation)
avg_realized_corr = calculate_average_realized_correlation(
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
)

# Calculate implied correlation (uses implied volatilities and index weights from weights.py)
# (used within dispersion calculation)
implied_corr_value = calculate_implied_correlation(
    "SPY",
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
    # Index weights are loaded internally from constituents-sp500.csv via weights.py
)

# Calculate correlation dispersion (used by the backtesting engine)
# Returns a dict with 'implied_correlation', 'realized_correlation', and 'correlation_dispersion'
dispersion_metrics = calculate_correlation_dispersion(
    "SPY",
    ["AAPL", "MSFT", "AMZN"],
    "2022-01-10",
    lookback=30
)
```
Index component weights are loaded from `constituents-sp500.csv` via `backtester.weights.py` for accurate implied correlation calculation.

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
    risk_free_rate=0.02,
    volatility_method="vix_implied"
)

# Or use custom volatility
custom_price = price_options(
    ticker="SPY",
    current_date="2022-01-10",
    expiration_date="2022-02-17",
    strike_price=450,
    option_type="call",
    volatility_method="custom",
    volatility_value=0.25
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
2. Initialize the `BacktestLogger` for logging.
3. Initialize the `RiskManager` with rules from `config.json`.
4. Initialize the `BacktestEngine`.
5. Run the backtest from start to end date, applying risk management rules.
6. Calculate and display performance metrics.
7. Save detailed results (portfolio history, trade history, summary report) to the `results/` directory (path configurable in `config.json`).
8. Generate and save plots (e.g., performance chart) to the `results/` directory.

#### Backtesting Engine

The engine processes each trading day by:
1. Updating the value of existing positions and checking for stop-losses via the `RiskManager`.
2. Checking for expired options and closing those positions.
3. Generating trading signals based on correlation dispersion (from `correlation.py`) or potentially DSPX signals (from `dspx.py`), if applicable. Signal generation is subject to `RiskManager` constraints (e.g., if new trades are allowed).
4. Executing trades based on signals, considering position sizing and risk limits from `RiskManager`.
5. Recording end-of-day portfolio values and trade details.
The `BacktestLogger` records activities throughout the backtest.

#### Trading Signals

The dispersion trading system uses two main types of entry signals:

1. **Standard Dispersion Trade** (when `dispersion > entry_threshold`):
   - Sell index options (collect premium)
   - Buy component options (pay premium)
   - Used when implied correlation is significantly higher than realized correlation

2. **Reverse Dispersion Trade** (when `dispersion < -entry_threshold` or equivalent DSPX signal):
   - Buy index options (pay premium)
   - Sell component options (collect premium)
   - Used when implied correlation is significantly lower than realized correlation

Positions are exited when:
- The disparity between implied and realized correlation (or DSPX signal) narrows below the `exit_threshold`
- Options reach their expiration date
- Risk limits defined in `RiskManager` are breached (e.g., stop-loss, max drawdown)

### Results Analysis

After running `python main.py`, the backtest results are saved in the directory specified by `paths.results_dir` in `config.json` (default is `results/`). This includes:
- `portfolio_history.csv`: Daily portfolio metrics.
- `trade_history.csv`: Detailed log of all trades.
- `summary.txt`: A summary of the backtest configuration and key performance metrics.
- Plots (e.g., performance chart) generated by `engine.plot_results()`.

You can then load and analyze these files. The `main.py` script already prints key performance metrics to the console.

```python
# Example of how main.py displays results (actual loading/analysis might use saved files)
import json
from backtester.engine import BacktestEngine # For context, not direct re-run here

# Assuming results are already generated by running 'python main.py'
# You would typically load the CSV files from the 'results/' directory with pandas

# Example metrics that main.py calculates and prints:
# Total Return, Annualized Return, Annualized Volatility, Sharpe Ratio, Max Drawdown, Final Portfolio Value.

# To re-plot (if needed, main.py does it automatically):
# with open('config.json', 'r') as f:
# config = json.load(f)
# engine = BacktestEngine(config) # This would re-initialize, not ideal for just plotting
# engine.plot_results() # Typically you'd have a separate script to load and plot saved data
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

The system uses index component weights from the `Weight` column in `constituents-sp500.csv` (via `backtester.weights.py`) for more accurate correlation calculations. These weights are used to:
- Calculate weighted implied volatility of the index.
- Properly weight components in implied correlation calculations.
- Generate more accurate dispersion signals.

## Known Issues and Limitations

- The system requires VIX data (`^VIX.csv`) for VIX-based implied volatility calculations.
- DSPX-based strategies require `DSPX_History.csv`.
- Short options positions have theoretically unlimited risk, though the `RiskManager` provides tools to mitigate this (see `README_RISK_MANAGEMENT.md`).
- Transaction cost modeling includes basic commission and fixed slippage (configurable in `config.json`). Market impact modeling can be enabled.
- No dividends handling in the current Black-Scholes and Binomial options pricing models.

## New Features Overview
- **Advanced Risk Management**: Comprehensive risk controls via `risk_manager.py` and `config.json`, detailed in `README_RISK_MANAGEMENT.md`.
- **DSPX Integration**: Support for strategies based on the CBOE S&P 500 Dispersion Index (DSPX) via `dspx.py` and `DSPX_History.csv`. See `methodology-cboe-sp-500-dispersion-index.pdf` for background.
- **Backtest Logging**: Customizable logging of backtest events using `logger.py`.

## Contributors

Clancy Hughes, chughe25@villanova.edu
