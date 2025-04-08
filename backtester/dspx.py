import pandas as pd
import numpy as np
import os
from datetime import datetime

def load_dspx_data(data_dir=None):
    """
    Load the DSPX (CBOE S&P 500 Dispersion) Index historical data
    
    Parameters:
    -----------
    data_dir : str, optional
        Directory containing the DSPX data file. If None, will look in project root.
    
    Returns:
    --------
    pandas.DataFrame
        Dataframe with DSPX data indexed by date
    """
    # Get the path to the data file
    if data_dir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dspx_file_path = os.path.join(project_root, 'DSPX_History.csv')
    else:
        dspx_file_path = os.path.join(data_dir, 'DSPX_History.csv')
    
    # Check if file exists
    if not os.path.exists(dspx_file_path):
        print(f"Warning: DSPX data file not found at {dspx_file_path}")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=['date', 'DSPX'])
    
    try:
        # Load the CSV data
        dspx_data = pd.read_csv(dspx_file_path)
        
        # Check if data is empty
        if len(dspx_data) == 0:
            print(f"Warning: DSPX data file is empty: {dspx_file_path}")
            return pd.DataFrame(columns=['date', 'DSPX'])
        
        # Convert date strings to datetime objects
        if 'DATE' in dspx_data.columns:
            dspx_data['DATE'] = pd.to_datetime(dspx_data['DATE'], format='%m/%d/%Y')
            # Rename columns for consistency
            dspx_data = dspx_data.rename(columns={'DATE': 'date'})
        elif 'Date' in dspx_data.columns:
            dspx_data['Date'] = pd.to_datetime(dspx_data['Date'])
            # Rename columns for consistency
            dspx_data = dspx_data.rename(columns={'Date': 'date'})
        
        # Make sure DSPX column exists
        if 'DSPX' not in dspx_data.columns:
            print("Warning: 'DSPX' column not found in data file. Looking for alternatives...")
            # Check for possible alternative column names
            index_cols = [col for col in dspx_data.columns if 'close' in col.lower() or 'value' in col.lower()]
            if index_cols:
                print(f"Using column '{index_cols[0]}' as DSPX value")
                dspx_data = dspx_data.rename(columns={index_cols[0]: 'DSPX'})
            else:
                print("No suitable column found for DSPX values")
                return pd.DataFrame(columns=['date', 'DSPX'])
        
        # Sort by date
        dspx_data = dspx_data.sort_values('date')
        
        print(f"Loaded DSPX data with {len(dspx_data)} entries (dspx.py).")
        return dspx_data
        
    except Exception as e:
        print(f"Error loading DSPX data: {str(e)}")
        return pd.DataFrame(columns=['date', 'DSPX'])

def calculate_dspx_signal(dspx_data, current_date, lookback=30, entry_threshold=1.0, exit_threshold=0.5):
    """
    Calculate trading signals based on DSPX index
    
    Parameters:
    -----------
    dspx_data : pandas.DataFrame
        Dataframe containing DSPX data
    current_date : datetime.date or str
        Current date for signal calculation
    lookback : int
        Number of days to look back for calculating moving average
    entry_threshold : float
        Threshold for entry signals (in standard deviations)
    exit_threshold : float
        Threshold for exit signals (in standard deviations)
        
    Returns:
    --------
    dict
        Dictionary containing signal information:
        - signal: Type of signal (ENTER_DISPERSION, ENTER_REVERSE_DISPERSION, EXIT, or None)
        - action: Action to take based on signal
        - metrics: Dictionary with DSPX value, z-score, and other metrics
    """
    # Convert date format if needed
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date).date()
    elif hasattr(current_date, 'date') and callable(getattr(current_date, 'date')):
        current_date = current_date.date()
    
    # Filter data up to current date
    historical_data = dspx_data[dspx_data['date'].dt.date <= current_date].copy()
    
    if len(historical_data) < lookback + 1:
        raise ValueError(f"Not enough historical DSPX data before {current_date}")
    
    # Get the current DSPX value
    current_dspx = historical_data.iloc[-1]['DSPX']
    
    # Calculate moving average and standard deviation
    lookback_data = historical_data.iloc[-lookback-1:-1]
    dspx_mean = lookback_data['DSPX'].mean()
    dspx_std = lookback_data['DSPX'].std()
    
    # Calculate z-score (how many standard deviations from mean)
    z_score = (current_dspx - dspx_mean) / dspx_std if dspx_std > 0 else 0
    
    # Generate signal based on z-score
    signal = None
    action = None
    
    if z_score > entry_threshold:
        # DSPX is significantly higher than average - positive dispersion
        # Indicates high implied correlation relative to realized correlation
        signal = 'ENTER_DISPERSION'
        action = 'SELL_INDEX_BUY_COMPONENTS'
    elif z_score < -entry_threshold:
        # DSPX is significantly lower than average - negative dispersion
        # Indicates low implied correlation relative to realized correlation
        signal = 'ENTER_REVERSE_DISPERSION'
        action = 'BUY_INDEX_SELL_COMPONENTS'
    elif abs(z_score) < exit_threshold:
        # DSPX has reverted to the mean - exit positions
        signal = 'EXIT'
        action = 'CLOSE_POSITIONS'
    
    # Compile metrics
    metrics = {
        'dspx_value': current_dspx,
        'dspx_mean': dspx_mean,
        'dspx_std': dspx_std,
        'z_score': z_score
    }
    
    # Return signal information
    if signal:
        return {
            'signal': signal,
            'action': action,
            'metrics': metrics
        }
    else:
        return None 