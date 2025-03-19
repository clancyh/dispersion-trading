import pandas as pd
import os

def load_index_weights(index_ticker='SPY'):
    """
    Load the constituent weights for an index from the constituents CSV file
    
    Parameters:
    -----------
    index_ticker : str
        Ticker symbol of the index (currently only SPY supported)
        
    Returns:
    --------
    dict
        Dictionary mapping ticker symbols to their weights (as decimals)
    """
    # Load the constituents file
    constituents_file = 'constituents-sp500.csv'
    if not os.path.exists(constituents_file):
        raise FileNotFoundError(f"Constituents file not found: {constituents_file}")
    
    # Read the file
    constituents_df = pd.read_csv(constituents_file)
    
    # Check if Weight column exists
    if 'Weight' not in constituents_df.columns:
        print(f"Warning: 'Weight' column not found in constituents file. Using equal weights.")
        # Generate equal weights for all constituents
        symbols = constituents_df['Symbol'].tolist()
        return {symbol: 1.0 / len(symbols) for symbol in symbols}
    
    # Convert weights from percentage strings to decimal values
    weights = {}
    for _, row in constituents_df.iterrows():
        # Remove '%' and convert to float
        weight_str = str(row['Weight']).strip('%')
        try:
            # Convert to decimal (e.g., "6.71%" -> 0.0671)
            weight_value = float(weight_str) / 100.0
            weights[row['Symbol']] = weight_value
        except ValueError:
            # Handle case where weight is not a valid number
            print(f"Warning: Invalid weight format for {row['Symbol']}. Using default.")
            weights[row['Symbol']] = 0.0
    
    # Normalize weights to ensure they sum to 1.0
    total_weight = sum(weights.values())
    if total_weight > 0:
        for symbol in weights:
            weights[symbol] = weights[symbol] / total_weight
    
    return weights 