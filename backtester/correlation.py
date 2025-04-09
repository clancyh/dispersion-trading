import pandas as pd
import numpy as np
import os
from datetime import datetime
from .volatility import calculate_historical_volatility, calculate_implied_volatilities
from .weights import load_index_weights

def calculate_realized_correlation(tickers, current_date, lookback=30):
    """
    Calculate the realized correlation matrix between a set of tickers
    
    Parameters:
    -----------
    tickers : list
        List of ticker symbols
    current_date : datetime or str
        Date up to which to calculate correlation
    lookback : int
        Number of days to look back for correlation calculation
        
    Returns:
    --------
    pandas.DataFrame
        Correlation matrix between tickers
    """
    # Convert date format if needed
    if isinstance(current_date, str):
        current_date = datetime.strptime(current_date, '%Y-%m-%d')
    elif hasattr(current_date, 'date') and callable(getattr(current_date, 'date')):
        # It's already a datetime object, do nothing
        pass
    elif hasattr(current_date, 'year') and not callable(getattr(current_date, 'date', None)):
        # It's a date object, convert to datetime
        current_date = datetime.combine(current_date, datetime.min.time())
    
    # Create a dataframe to store returns
    all_returns = pd.DataFrame()
    
    # Get returns for each ticker
    for ticker in tickers:
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
        
        # Add to dataframe
        all_returns[ticker] = recent_returns.values
    
    # Calculate correlation matrix
    corr_matrix = all_returns.corr()
    
    return corr_matrix

def calculate_average_realized_correlation(component_tickers, current_date, lookback=30):
    """
    Calculate the average realized correlation between components
    
    Parameters:
    -----------
    component_tickers : list
        List of component ticker symbols
    current_date : datetime or str
        Date up to which to calculate correlation
    lookback : int
        Number of days to look back for correlation calculation
        
    Returns:
    --------
    float
        Average realized correlation
    """
    # Calculate correlation matrix
    corr_matrix = calculate_realized_correlation(component_tickers, current_date, lookback)
    
    # Get the average of all pairwise correlations (excluding self-correlations)
    n = len(component_tickers)
    if n <= 1:
        return 0.0  # No correlation with just one component
    
    total_corr = 0.0
    count = 0
    
    for i in range(n):
        for j in range(i+1, n):
            total_corr += corr_matrix.iloc[i, j]
            count += 1
    
    # Return average
    return total_corr / count if count > 0 else 0.0

def calculate_implied_correlation(index_ticker, component_tickers, current_date, lookback=30, weights=None):
    """
    Calculate the implied correlation between index components using implied volatilities
    
    Parameters:
    -----------
    index_ticker : str
        Ticker symbol of the index
    component_tickers : list
        List of component ticker symbols
    current_date : datetime or str
        Date for which to calculate correlation
    lookback : int
        Number of days to look back for volatility calculation
    weights : dict, optional
        Dictionary of component weights in the index
        
    Returns:
    --------
    float
        Implied correlation
    """
    # Get implied volatilities
    implied_vols = calculate_implied_volatilities(index_ticker, component_tickers, current_date, lookback)
    
    # If weights are not provided, load them from the constituents file
    if weights is None:
        try:
            all_weights = load_index_weights(index_ticker)
            # Filter weights to include only the components we're analyzing
            weights = {}
            weight_sum = 0
            for ticker in component_tickers:
                if ticker in all_weights:
                    weights[ticker] = all_weights[ticker]
                    weight_sum += weights[ticker]
                    
            # Normalize weights if we don't have all components
            if weight_sum > 0 and weight_sum < 1.0:
                for ticker in weights:
                    weights[ticker] = weights[ticker] / weight_sum
        except Exception as e:
            print(f"Warning: Could not load index weights: {e}. Using equal weights.")
            weights = {ticker: 1.0 / len(component_tickers) for ticker in component_tickers}
    
    # Calculate the weighted sum of individual variances
    weighted_var_sum = 0.0
    for ticker in component_tickers:
        if ticker in weights and ticker in implied_vols:
            weighted_var_sum += weights[ticker]**2 * implied_vols[ticker]**2
    
    # Calculate the cross-term denominator (sum of weighted vol products)
    cross_term_denom = 0.0
    
    for i, ticker1 in enumerate(component_tickers):
        for j in range(i+1, len(component_tickers)):
            ticker2 = component_tickers[j]
            cross_term_denom += 2 * weights[ticker1] * weights[ticker2] * implied_vols[ticker1] * implied_vols[ticker2]
    
    # Calculate index variance
    index_var = implied_vols[index_ticker]**2
    
    # If denominator is too small, return 0 correlation
    if cross_term_denom < 1e-10:
        return 0.0
    
    # Calculate implied correlation using the variance formula
    implied_corr = (index_var - weighted_var_sum) / cross_term_denom
    
    # Bound correlation between -1 and 1
    implied_corr = max(-1.0, min(1.0, implied_corr))
    
    return implied_corr 

def calculate_correlation_dispersion(index_ticker, component_tickers, current_date, lookback=30):
    """
    Calculate the dispersion between implied and realized correlation
    
    Parameters:
    -----------
    index_ticker : str
        Ticker symbol of the index
    component_tickers : list
        List of component ticker symbols
    current_date : datetime or str
        Date for which to calculate correlation dispersion
    lookback : int
        Number of days to look back for correlation calculation
        
    Returns:
    --------
    dict
        Dictionary containing the correlation metrics:
        - implied_correlation: Correlation implied by options prices
        - realized_correlation: Historical realized correlation
        - correlation_dispersion: Difference between implied and realized correlation
    """
    # Calculate implied correlation
    implied_corr = calculate_implied_correlation(
        index_ticker,
        component_tickers,
        current_date,
        lookback=lookback
    )
    
    print(f"Implied correlation: {implied_corr:.4f}")

    # Calculate realized correlation
    realized_corr = calculate_average_realized_correlation(
        component_tickers,
        current_date,
        lookback=lookback
    )
    
    # Calculate dispersion (implied minus realized)
    dispersion = implied_corr - realized_corr
    
    print(f"Realized correlation: {realized_corr:.4f}")
    print(f"Correlation dispersion: {dispersion:.4f}")
    
    # Return all metrics
    return {
        'implied_correlation': implied_corr,
        'realized_correlation': realized_corr,
        'correlation_dispersion': dispersion
    } 