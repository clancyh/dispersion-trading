import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, '..', '..', 'results', 'aligned_strategy_and_benchmark.csv')
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'plots')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'march_2020_performance.png')

START_DATE = '2020-03-01'
END_DATE = '2020-03-31'

def ensure_output_dir_exists():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def plot_march_2020_performance(data_file, output_file, start_date_str, end_date_str):
    """
    Plots normalized performance of strategy and benchmark during a specific period (e.g., March 2020).
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

    # Filter for the specific period
    mask = (df.index >= start_date_str) & (df.index <= end_date_str)
    period_df = df.loc[mask]

    if period_df.empty:
        print(f"Error: No data found for the period {start_date_str} to {end_date_str}.")
        return

    # Normalize the values at the start of the period to 100
    normalized_portfolio = (period_df['portfolio_value'] / period_df['portfolio_value'].iloc[0]) * 100
    normalized_benchmark = (period_df['spy_benchmark_value'] / period_df['spy_benchmark_value'].iloc[0]) * 100

    # Ensure output directory exists
    ensure_output_dir_exists()

    # Create figure
    plt.figure(figsize=(12, 7))
    
    plt.plot(period_df.index, normalized_portfolio, label='Strategy Normalized Performance', color='blue')
    plt.plot(period_df.index, normalized_benchmark, label='Benchmark Normalized Performance (SPY)', color='red', linestyle='--')
    
    plt.title(f'Performance During {pd.to_datetime(start_date_str).strftime("%B %Y")}', fontsize=16)
    plt.xlabel('Date')
    plt.ylabel('Normalized Value (Start of Period = 100)')
    plt.grid(True)
    plt.legend()
    
    # Format x-axis dates for daily data within a month
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=5)) # Show a date every 5 days
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
    plot_march_2020_performance(DATA_FILE, OUTPUT_FILE, START_DATE, END_DATE) 