# this file will contain the universe of stocks that we will be trading
# it will be a list of tickers that we will be trading
# those tickers will be loaded using the data/datagrab.r script
# it will be the first step of the backtester

import pandas as pd
import random
import subprocess
import os
import json

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
                "seed": 42
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
                "seed": 42
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

# Grab data for index ETF and VIX
grab_data(f"{index},^VIX", start_date, end_date)

# Grab data for selected tickers 
grab_data(",".join(selected_tickers), start_date, end_date)

# Data will be saved to data/processed/ directory as CSV files
print(f"Universe setup complete. Selected tickers: {index} + {len(selected_tickers)} constituents")
print(f"Date range: {start_date} to {end_date}")