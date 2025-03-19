import pandas as pd
import numpy as np
import os
from datetime import datetime

def calculate_historical_volatility(ticker, current_date, lookback=30):
    """
    Calculate historical volatility for a ticker
    
    Parameters:
    -----------
    ticker : str
        Ticker symbol
    current_date : datetime or str
        Date up to which to calculate volatility
    lookback : int
        Number of days to look back for volatility calculation
    
    Returns:
    --------
    float
        Annualized historical volatility
    """
    # Convert date format if needed
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    
    # Load data
    data_file = f'data/processed/{ticker}.csv'
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Historical data for {ticker} not found.")
        
    data = pd.read_csv(data_file)
    data['date'] = pd.to_datetime(data['date'])
    
    # Filter data up to current date
    data = data[data['date'] <= current_date]
    
    if len(data) < lookback + 1:
        raise ValueError(f"Not enough historical data for {ticker} before {current_date}")
    
    # Calculate returns
    returns = data['Adjusted'].pct_change().dropna()
    
    # Use the most recent lookback period
    recent_returns = returns.iloc[-lookback:]
    
    # Calculate and return annualized volatility
    return recent_returns.std() * np.sqrt(252)

def calculate_vix_implied_volatility(ticker, current_date, lookback=30):
    """
    Calculate implied volatility using VIX as a scaling factor
    
    Parameters:
    -----------
    ticker : str
        Ticker symbol
    current_date : datetime or str
        Date for which to calculate implied volatility
    lookback : int
        Number of days to look back for historical volatility calculation
    
    Returns:
    --------
    float
        Estimated implied volatility
    """
    # Convert date format if needed
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    
    # Check for VIX data
    vix_file = 'data/processed/^VIX.csv'
    if not os.path.exists(vix_file):
        raise FileNotFoundError("VIX data not found. Please run datagrab.r with '^VIX' included.")
    
    # Load VIX data
    vix_data = pd.read_csv(vix_file)
    vix_data['date'] = pd.to_datetime(vix_data['date'])
    
    # Get latest VIX value as of current_date
    vix_filtered = vix_data[vix_data['date'] <= current_date]
    if len(vix_filtered) == 0:
        raise ValueError(f"No VIX data available on or before {current_date}")
        
    vix_value = vix_filtered.iloc[-1]['Adjusted']
    
    # Load SPY data as market reference
    spy_file = 'data/processed/SPY.csv'
    if not os.path.exists(spy_file):
        raise FileNotFoundError("SPY data not found. Please run datagrab.r with 'SPY' included.")
    
    # Calculate SPY historical volatility
    spy_hist_vol = calculate_historical_volatility('SPY', current_date, lookback)
    
    # Calculate the volatility risk premium (VIX is quoted in percentage points)
    vol_risk_premium = vix_value / 100 / spy_hist_vol
    
    # Calculate historical volatility for the target ticker
    ticker_hist_vol = calculate_historical_volatility(ticker, current_date, lookback)
    
    # Apply volatility risk premium to get implied volatility
    implied_vol = ticker_hist_vol * vol_risk_premium
    
    # For very low VIX environments, ensure a minimum level of implied vol
    # This is a safeguard against unrealistically low implied vol estimates
    min_premium = 1.05  # Implied vol should be at least 5% higher than historical
    if vol_risk_premium < min_premium:
        implied_vol = ticker_hist_vol * min_premium
    
    return implied_vol

def calculate_implied_volatilities(index_ticker, component_tickers, current_date, lookback=30):
    """
    Calculate implied volatilities for an index and its components
    
    Parameters:
    -----------
    index_ticker : str
        Ticker symbol of the index
    component_tickers : list
        List of component ticker symbols
    current_date : datetime or str
        Date for which to calculate implied volatilities
    lookback : int
        Number of days to look back for historical volatility calculation
    
    Returns:
    --------
    dict
        Dictionary of implied volatilities for index and components
    """
    # Initialize results dictionary
    implied_vols = {}
    
    # Calculate implied vol for the index
    implied_vols[index_ticker] = calculate_vix_implied_volatility(index_ticker, current_date, lookback)
    
    # Calculate implied vol for each component
    for ticker in component_tickers:
        implied_vols[ticker] = calculate_vix_implied_volatility(ticker, current_date, lookback)
    
    return implied_vols 