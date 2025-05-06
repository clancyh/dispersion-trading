import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from scipy.stats import skew, kurtosis

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', '..', 'results', 'aligned_strategy_and_benchmark.csv')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'plots')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'returns_distribution.png')

BINS = 100 # Number of bins for the histogram

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def plot_returns_distribution(data_file, output_file):
    """
    Plots histograms of daily returns for the strategy and benchmark.
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

    portfolio_returns = df['portfolio_returns']
    benchmark_returns = df['benchmark_returns']

    # Ensure output directory exists
    ensure_output_dir_exists()

    # Calculate statistics
    stats_portfolio = {
        'Mean': portfolio_returns.mean(),
        'Std Dev': portfolio_returns.std(),
        'Skewness': skew(portfolio_returns),
        'Kurtosis': kurtosis(portfolio_returns) # Fisher's kurtosis (normal is 0)
    }
    stats_benchmark = {
        'Mean': benchmark_returns.mean(),
        'Std Dev': benchmark_returns.std(),
        'Skewness': skew(benchmark_returns),
        'Kurtosis': kurtosis(benchmark_returns)
    }

    # Create figure
    plt.figure(figsize=(12, 7))
    
    plt.hist(portfolio_returns, bins=BINS, alpha=0.7, label='Strategy Returns', density=True, color='blue')
    plt.hist(benchmark_returns, bins=BINS, alpha=0.7, label='Benchmark Returns', density=True, color='red')
    
    plt.title('Distribution of Daily Returns', fontsize=16)
    plt.xlabel('Daily Return')
    plt.ylabel('Density')
    plt.grid(True, alpha=0.5)
    plt.legend()

    # Add statistics to the plot
    text_portfolio = 'Strategy:\n' + '\n'.join([f'{k}: {v:.4f}' for k, v in stats_portfolio.items()])
    text_benchmark = 'Benchmark:\n' + '\n'.join([f'{k}: {v:.4f}' for k, v in stats_benchmark.items()])
    
    plt.text(0.05, 0.95, text_portfolio, transform=plt.gca().transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.5))
    plt.text(0.05, 0.70, text_benchmark, transform=plt.gca().transAxes, fontsize=9,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.5', fc='lightcoral', alpha=0.5))

    plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.1f}%'))
    
    plt.tight_layout()

    # Save the plot
    try:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    
    plt.close() # Close the figure to free memory

if __name__ == '__main__':
    plot_returns_distribution(DATA_FILE, OUTPUT_FILE) 