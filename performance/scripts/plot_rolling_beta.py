import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', '..', 'results', 'aligned_strategy_and_benchmark.csv')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'plots')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'rolling_beta.png')

ROLLING_WINDOW = 252 # 1-year rolling window

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def calculate_rolling_beta(strategy_returns: pd.Series, benchmark_returns: pd.Series, window: int) -> pd.Series:
    """Calculates the rolling beta of strategy returns with respect to benchmark returns."""
    # Rolling covariance between strategy and benchmark
    rolling_cov = strategy_returns.rolling(window=window).cov(benchmark_returns)
    # Rolling variance of benchmark
    rolling_var_benchmark = benchmark_returns.rolling(window=window).var()
    
    rolling_beta = rolling_cov / rolling_var_benchmark
    return rolling_beta.dropna()

def plot_rolling_beta(data_file, output_file):
    """
    Plots the rolling beta for the strategy.
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

    # Calculate rolling beta
    df['rolling_beta'] = calculate_rolling_beta(df['portfolio_returns'], df['benchmark_returns'], ROLLING_WINDOW)

    # Create figure
    plt.figure(figsize=(12, 6))
    
    plt.plot(df.index, df['rolling_beta'], label=f'Strategy Rolling Beta ({ROLLING_WINDOW}-day)', color='green')
    
    plt.title(f'{ROLLING_WINDOW}-Day Rolling Beta vs. Benchmark', fontsize=16)
    plt.xlabel('Date')
    plt.ylabel('Rolling Beta')
    plt.axhline(0, color='grey', linestyle='--', linewidth=0.8)
    plt.axhline(1, color='grey', linestyle='--', linewidth=0.8)
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
    plot_rolling_beta(DATA_FILE, OUTPUT_FILE) 