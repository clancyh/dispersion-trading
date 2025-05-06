import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', '..', 'results', 'aligned_strategy_and_benchmark.csv')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'plots')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'rolling_sharpe_ratio.png')

TRADING_DAYS_PER_YEAR = 252
ROLLING_WINDOW = TRADING_DAYS_PER_YEAR # 1-year rolling window
RISK_FREE_RATE_DAILY = 0.0 / TRADING_DAYS_PER_YEAR # Assuming 0% annual risk-free rate

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def calculate_rolling_sharpe(returns_series: pd.Series, window: int, risk_free_rate_daily: float, trading_days_per_year: int) -> pd.Series:
    """Calculates the annualized rolling Sharpe ratio for a returns series."""
    rolling_mean_returns = returns_series.rolling(window=window).mean()
    rolling_std_returns = returns_series.rolling(window=window).std()
    
    # Calculate daily Sharpe ratio
    daily_sharpe_ratio = (rolling_mean_returns - risk_free_rate_daily) / rolling_std_returns
    
    # Annualize the Sharpe ratio
    annualized_sharpe_ratio = daily_sharpe_ratio * np.sqrt(trading_days_per_year)
    return annualized_sharpe_ratio.dropna()

def plot_rolling_sharpe(data_file, output_file):
    """
    Plots rolling Sharpe ratios for the strategy and benchmark.
    """
    try:
        df = pd.read_csv(data_file)
    except FileNotFoundError:
        print(f"Error: Data file not found at {data_file}")
        return

    if not {'date', 'portfolio_value', 'spy_benchmark_value'}.issubset(df.columns):
        print("Error: CSV must contain 'date', 'portfolio_value', and 'spy_benchmark_value' columns.")
        return

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').set_index('date')

    # Calculate daily returns
    df['portfolio_returns'] = df['portfolio_value'].pct_change()
    df['benchmark_returns'] = df['spy_benchmark_value'].pct_change()
    df = df.dropna() # Drop first row with NaN returns

    # Ensure output directory exists
    ensure_output_dir_exists()

    # Calculate rolling Sharpe ratios
    df['portfolio_rolling_sharpe'] = calculate_rolling_sharpe(df['portfolio_returns'], ROLLING_WINDOW, RISK_FREE_RATE_DAILY, TRADING_DAYS_PER_YEAR)
    df['benchmark_rolling_sharpe'] = calculate_rolling_sharpe(df['benchmark_returns'], ROLLING_WINDOW, RISK_FREE_RATE_DAILY, TRADING_DAYS_PER_YEAR)

    # Create figure
    plt.figure(figsize=(12, 6))
    
    plt.plot(df.index, df['portfolio_rolling_sharpe'], label=f'Strategy Rolling Sharpe ({ROLLING_WINDOW}-day)', color='blue')
    plt.plot(df.index, df['benchmark_rolling_sharpe'], label=f'Benchmark Rolling Sharpe ({ROLLING_WINDOW}-day)', color='red', linestyle='--')
    
    plt.title(f'{ROLLING_WINDOW}-Day Rolling Sharpe Ratios', fontsize=16)
    plt.xlabel('Date')
    plt.ylabel('Annualized Sharpe Ratio')
    plt.grid(True)
    plt.legend()
    
    # Format x-axis dates
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    
    plt.tight_layout()

    # Save the plot
    try:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    
    plt.close() # Close the figure to free memory

if __name__ == '__main__':
    plot_rolling_sharpe(DATA_FILE, OUTPUT_FILE) 