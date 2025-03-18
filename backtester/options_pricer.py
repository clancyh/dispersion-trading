# this file will contain the options pricer
# it will be used to price the options for the selected tickers
# it should take in a ticker, the current date, the expiration date, and the strike price
# it should return the price of the option

# import the necessary libraries
import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime
import os

# define the overall function to price the options
def price_options(ticker, current_date, expiration_date, strike_price, option_type='call', 
                  model='black_scholes', risk_free_rate=0.02, steps=100):
    """
    Price options using either Black-Scholes or Binomial Tree model
    
    Parameters:
    -----------
    ticker : str
        The ticker symbol of the underlying asset
    current_date : str or datetime
        The current date (for pricing)
    expiration_date : str or datetime
        The expiration date of the option
    strike_price : float
        The strike price of the option
    option_type : str, optional
        'call' or 'put', default is 'call'
    model : str, optional
        'black_scholes' or 'binomial', default is 'black_scholes'
    risk_free_rate : float, optional
        Annual risk-free rate as a decimal, default is 0.02 (2%)
    steps : int, optional
        Number of steps for binomial tree model, default is 100
        
    Returns:
    --------
    float
        The price of the option
    """
    # Convert dates to datetime objects if they are strings
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    if isinstance(expiration_date, str):
        expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d')
    
    # Check if data file exists
    data_file = f'data/processed/{ticker}.csv'
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Historical data for {ticker} not found. Please run datagrab.r first.")
    
    # Load the historical data for the ticker
    data = pd.read_csv(data_file)
    data['date'] = pd.to_datetime(data['date'])
    
    # Filter data up to current_date
    data = data[data['date'] <= current_date]
    
    if len(data) < 30:  # Need enough data to calculate volatility
        raise ValueError(f"Not enough historical data for {ticker} before {current_date}")
    
    # Get the current price of the stock
    current_price = data.iloc[-1]['Adjusted']
    
    # Calculate the daily returns
    returns = data['Adjusted'].pct_change().dropna()
    
    # Calculate the annualized volatility (standard deviation of returns)
    volatility = returns.std() * np.sqrt(252)
    
    # Calculate time to expiration in years
    time_to_expiry = (expiration_date - current_date).days / 365.0
    
    # Check for invalid time to expiry
    if time_to_expiry <= 0:
        raise ValueError("Expiration date must be after current date")
    
    # Price the option using selected model
    if model.lower() == 'black_scholes':
        price = black_scholes(current_price, strike_price, time_to_expiry, 
                              risk_free_rate, volatility, option_type)
    elif model.lower() == 'binomial':
        price = binomial_tree(current_price, strike_price, time_to_expiry, 
                              risk_free_rate, volatility, steps, option_type)
    else:
        raise ValueError("Model must be either 'black_scholes' or 'binomial'")
    
    return price

def black_scholes(S, K, T, r, sigma, option_type='call'):
    """
    Calculate the price of a European option using the Black-Scholes formula
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free rate (annual)
    sigma : float
        Volatility of the underlying asset (annual)
    option_type : str
        'call' for call option, 'put' for put option
        
    Returns:
    --------
    float
        Option price
    """
    # Calculate d1 and d2
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Calculate option price based on type
    if option_type.lower() == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    elif option_type.lower() == 'put':
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        raise ValueError("Option type must be either 'call' or 'put'")
    
    return price

def binomial_tree(S, K, T, r, sigma, steps, option_type='call'):
    """
    Calculate the price of an American option using the Binomial Tree model
    
    Parameters:
    -----------
    S : float
        Current stock price
    K : float
        Strike price
    T : float
        Time to expiration in years
    r : float
        Risk-free rate (annual)
    sigma : float
        Volatility of the underlying asset (annual)
    steps : int
        Number of time steps in the binomial tree
    option_type : str
        'call' for call option, 'put' for put option
        
    Returns:
    --------
    float
        Option price
    """
    # Time step
    dt = T / steps
    
    # Calculate up and down factors
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    
    # Risk-neutral probability
    p = (np.exp(r * dt) - d) / (u - d)
    
    # Initialize asset prices at final step
    asset_prices = np.zeros(steps + 1)
    for i in range(steps + 1):
        asset_prices[i] = S * (u ** (steps - i)) * (d ** i)
    
    # Initialize option values at final step
    option_values = np.zeros(steps + 1)
    for i in range(steps + 1):
        if option_type.lower() == 'call':
            option_values[i] = max(0, asset_prices[i] - K)
        elif option_type.lower() == 'put':
            option_values[i] = max(0, K - asset_prices[i])
        else:
            raise ValueError("Option type must be either 'call' or 'put'")
    
    # Backward induction to calculate option price
    for step in range(steps - 1, -1, -1):
        for i in range(step + 1):
            # Calculate asset price at this node
            asset_price = S * (u ** (step - i)) * (d ** i)
            
            # Calculate option value at this node using risk-neutral valuation
            option_value = np.exp(-r * dt) * (p * option_values[i] + (1 - p) * option_values[i + 1])
            
            # For American options, check if early exercise is optimal
            if option_type.lower() == 'call':
                exercise_value = max(0, asset_price - K)
            else:  # put
                exercise_value = max(0, K - asset_price)
            
            # Option value is the maximum of holding or exercising
            option_values[i] = max(option_value, exercise_value)
    
    # Return the option price at the initial node
    return option_values[0]

# Helper function to get stock price for a specific date
def get_stock_price(ticker, date):
    """
    Get the adjusted closing price for a ticker on a specific date
    
    Parameters:
    -----------
    ticker : str
        The ticker symbol
    date : str or datetime
        The date to get the price for
        
    Returns:
    --------
    float
        The adjusted closing price
    """
    data_file = f'data/processed/{ticker}.csv'
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Historical data for {ticker} not found. Please run datagrab.r first.")
    
    data = pd.read_csv(data_file)
    data['date'] = pd.to_datetime(data['date'])
    
    # Get exact date or closest previous date
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    
    # Filter for dates <= requested date and get the last entry
    matching_data = data[data['date'] <= date]
    
    if len(matching_data) == 0:
        raise ValueError(f"No data available for {ticker} on or before {date}")
    
    # Return the adjusted closing price
    return matching_data.iloc[-1]['Adjusted']


