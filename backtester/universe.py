# this file will contain the universe of stocks that we will be trading
# it will be a list of tickers that we will be trading
# those tickers will be loaded using the data/datagrab.r script
# it will be the first step of the backtester

import pandas as pd
import random
import subprocess
import os
import json
from datetime import datetime, timedelta

# Load configuration
def load_config(config_path='config.json'):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Config file not found at {config_path}. Using default settings.")
        return {
            "backtest": {
                "start_date": "2020-01-01",
                "end_date": "2024-12-31"
            },
            "universe": {
                "index": "SPY",
                "num_stocks": 10,
                "seed": 42,
                "repull_data": True
            }
        }
    except json.JSONDecodeError:
        print(f"Error parsing {config_path}. Using default settings.")
        return {
            "backtest": {
                "start_date": "2020-01-01",
                "end_date": "2024-12-31"
            },
            "universe": {
                "index": "SPY",
                "num_stocks": 10,
                "seed": 42,
                "repull_data": True
            }
        }

# Load configuration
config = load_config()

# Get parameters from config
start_date = config['backtest']['start_date']
end_date = config['backtest']['end_date']
index = config['universe']['index']
num_stocks = config['universe']['num_stocks']
random_seed = config['universe'].get('seed', None)
repull_data = config['universe'].get('repull_data', True)

# Set random seed if specified
if random_seed is not None:
    random.seed(random_seed)

# Read constituents from CSV file
constituents_df = pd.read_csv('constituents-sp500.csv')

# Extract symbols into a list
constituents = constituents_df['Symbol'].tolist()

# Select tickers according to config
if config['universe'].get('random_selection', True):
    # Shuffle the list of constituents
    random.shuffle(constituents)
    # Select the first n tickers
    selected_tickers = constituents[:num_stocks]
else:
    # In the future, could implement other selection methods here
    selected_tickers = constituents[:num_stocks]

# Function to grab data using the R script
def grab_data(symbols, start_date=None, end_date=None):
    # Build command
    cmd = ["Rscript", "data/datagrab.r"]
    
    # Add symbols as comma-separated string
    if isinstance(symbols, list):
        symbols = ",".join(symbols)
    cmd.append(symbols)
    
    # Add dates if provided
    if start_date:
        cmd.append(start_date)
    if end_date:
        cmd.append(end_date)
        
    # Run R script
    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully grabbed data for {symbols}")
    except subprocess.CalledProcessError as e:
        print(f"Error running R script: {e}")
        raise

# Function to check if data exists for all tickers
def data_exists_for_tickers(tickers, index_ticker, vix=True):
    all_tickers = tickers + [index_ticker]
    if vix:
        all_tickers.append("^VIX")
    
    for ticker in all_tickers:
        data_file = f'data/processed/{ticker}.csv'
        if not os.path.exists(data_file):
            print(f"Missing data file for {ticker}")
            return False
    return True

# Calculate extended start date (2 years before backtest start date)
backtest_start = datetime.strptime(start_date, '%Y-%m-%d')
extended_start = (backtest_start - timedelta(days=5*365)).strftime('%Y-%m-%d')

# Check if we need to pull data
if repull_data:
    print(f"Fetching index and VIX data with extended history (from {extended_start} to {end_date})")
    
    # Grab data for index ETF and VIX with extended history
    grab_data(f"{index},^VIX", extended_start, end_date)
    
    # Grab data for selected tickers (only for the backtest period)
    grab_data(",".join(selected_tickers), extended_start, end_date)
    
    print(f"Universe setup complete. Selected tickers: {index} + {len(selected_tickers)} constituents")
    print(f"Date range for components: {start_date} to {end_date}")
    print(f"Extended date range for index and VIX: {extended_start} to {end_date}")
else:
    print("Using existing data files (repull_data = False)")
    
    # Verify that all required data files exist
    if not data_exists_for_tickers(selected_tickers, index):
        print("WARNING: Some required data files are missing! Consider setting repull_data to True.")
    else:
        print(f"All required data files found for {index} + {len(selected_tickers)} constituents")