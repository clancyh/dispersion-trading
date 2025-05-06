import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', '..', 'results', 'aligned_strategy_and_benchmark.csv')
OUTPUT_DIR_NAME = 'plots'
OUTPUT_DIR = os.path.join(SCRIPT_DIR, OUTPUT_DIR_NAME)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'strategy_vs_benchmark_performance.png')

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        # This will create performance/scripts/plots if it doesn't exist
        os.makedirs(OUTPUT_DIR)

def calculate_drawdowns(series: pd.Series) -> pd.Series:
    """Calculates the drawdown series from a value series."""
    cumulative_returns = series / series.iloc[0] # Normalize to get cumulative returns if not already
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns - peak) / peak
    return drawdown

def plot_performance_and_drawdowns(data_file, output_file):
    """
    Plots cumulative performance and drawdowns for strategy and benchmark.
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

    # Ensure output directory exists
    ensure_output_dir_exists()

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [2, 1]})
    fig.suptitle('Strategy vs. Benchmark Performance Analysis', fontsize=16)

    # Plot 1: Cumulative Performance (Value)
    ax1.plot(df.index, df['portfolio_value'], label='Strategy Value', color='blue')
    ax1.plot(df.index, df['spy_benchmark_value'], label='Benchmark Value (SPY)', color='red', linestyle='--')
    ax1.set_title('Cumulative Performance')
    ax1.set_ylabel('Value')
    ax1.grid(True)
    ax1.legend()
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}')) # Format as integer

    # Calculate and Plot 2: Drawdowns
    df['portfolio_drawdown'] = calculate_drawdowns(df['portfolio_value'])
    df['benchmark_drawdown'] = calculate_drawdowns(df['spy_benchmark_value'])
    
    ax2.plot(df.index, df['portfolio_drawdown'] * 100, label='Strategy Drawdown', color='blue')
    ax2.fill_between(df.index, df['portfolio_drawdown'] * 100, 0, color='blue', alpha=0.1)
    ax2.plot(df.index, df['benchmark_drawdown'] * 100, label='Benchmark Drawdown (SPY)', color='red', linestyle='--')
    ax2.fill_between(df.index, df['benchmark_drawdown'] * 100, 0, color='red', alpha=0.1)
    ax2.set_title('Drawdowns')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(True)
    ax2.legend()
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

    # Format x-axis dates for both subplots
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.set_xlabel('Date')

    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Adjust for suptitle

    # Save the plot
    try:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    except Exception as e:
        print(f"Error saving plot: {e}")
    
    plt.close(fig) # Close the figure to free memory

if __name__ == '__main__':
    # Paths are now defined globally and are absolute or relative to script location
    plot_performance_and_drawdowns(DATA_FILE, OUTPUT_FILE) 