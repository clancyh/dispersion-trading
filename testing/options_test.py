#!/usr/bin/env python3
"""
Options Pricing Test Script
---------------------------
This script tests the options pricing functions using historical SPY data.
It prices options at different dates with various strikes and expiration dates,
using both Black-Scholes and Binomial models.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from options_pricer import price_options, black_scholes, binomial_tree

def main():
    print("Options Pricing Test Script")
    print("==========================\n")
    
    # Verify SPY data exists
    spy_data_path = 'data/processed/SPY.csv'
    if not os.path.exists(spy_data_path):
        print(f"Error: SPY data file not found at {spy_data_path}")
        return
    
    # Load SPY data
    spy_data = pd.read_csv(spy_data_path)
    spy_data['date'] = pd.to_datetime(spy_data['date'])
    
    print(f"Loaded SPY data from {spy_data['date'].min()} to {spy_data['date'].max()}")
    print(f"Total days: {len(spy_data)}\n")
    
    # Test parameters
    test_dates = [
        "2024-04-01",  # Early in dataset
        "2024-07-15",  # Mid-year point
        "2024-11-01",  # Later in dataset
        "2025-01-15"   # Near the end
    ]
    
    expiration_periods = [
        30,    # ~1 month
        60,    # ~2 months
        90,    # ~3 months
        180    # ~6 months
    ]
    
    # Test different scenarios
    for date_str in test_dates:
        current_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Get the current price from the data
        try:
            current_price_row = spy_data[spy_data['date'] <= current_date].iloc[-1]
            current_price = current_price_row['Adjusted']
            print(f"\nTesting options pricing as of {date_str} (SPY price: ${current_price:.2f})")
            print("-" * 70)
            
            # Generate various strike prices
            strikes = [
                round(current_price * 0.9),  # In-the-money for calls
                round(current_price),        # At-the-money
                round(current_price * 1.1)   # Out-of-the-money for calls
            ]
            
            # Print header
            print(f"{'Expiry':<12} {'Days':<6} {'Type':<6} {'Strike':<8} {'BS Price':<10} {'Binomial':<10} {'Diff %':<8}")
            print("-" * 70)
            
            # Test different expiration dates
            for days in expiration_periods:
                expiration_date = current_date + timedelta(days=days)
                expiration_str = expiration_date.strftime('%Y-%m-%d')
                
                # Skip if expiration date is beyond our data
                if expiration_date > spy_data['date'].max():
                    print(f"Skipping {expiration_str} (beyond data range)")
                    continue
                
                for strike in strikes:
                    for option_type in ['call', 'put']:
                        # Price using both models
                        bs_price = price_options(
                            'SPY', current_date, expiration_date, strike, 
                            option_type=option_type, model='black_scholes'
                        )
                        
                        bin_price = price_options(
                            'SPY', current_date, expiration_date, strike, 
                            option_type=option_type, model='binomial'
                        )
                        
                        # Calculate difference between models as percentage
                        if bs_price > 0:
                            diff_pct = abs(bs_price - bin_price) / bs_price * 100
                        else:
                            diff_pct = 0
                            
                        # Print results
                        print(f"{expiration_str:<12} {days:<6} {option_type:<6} "
                              f"${strike:<7.2f} ${bs_price:<9.2f} ${bin_price:<9.2f} {diff_pct:<8.2f}%")
                
        except Exception as e:
            print(f"Error testing date {date_str}: {e}")
    
    # Test extreme scenarios
    print("\nTesting Extreme Scenarios")
    print("-" * 70)
    
    try:
        # Deep in-the-money call
        test_deep_itm(spy_data, "2024-06-01", 60, 0.8, "call")
        
        # Deep out-of-the-money put
        test_deep_itm(spy_data, "2024-06-01", 60, 1.2, "put")
        
        # Very short expiration
        test_short_expiry(spy_data, "2024-09-01", 7)
        
        # Long expiration
        test_long_expiry(spy_data, "2024-04-01", 300)
        
    except Exception as e:
        print(f"Error in extreme scenarios: {e}")

def test_deep_itm(data, date_str, days_to_expiry, strike_multiplier, option_type):
    """Test deep in/out of the money options"""
    current_date = datetime.strptime(date_str, '%Y-%m-%d')
    expiration_date = current_date + timedelta(days=days_to_expiry)
    
    if current_date < data['date'].min() or current_date > data['date'].max():
        print(f"Date {date_str} out of range, skipping test")
        return
        
    current_price_row = data[data['date'] <= current_date].iloc[-1]
    current_price = current_price_row['Adjusted']
    strike = round(current_price * strike_multiplier)
    
    bs_price = price_options('SPY', current_date, expiration_date, strike, 
                           option_type=option_type, model='black_scholes')
    bin_price = price_options('SPY', current_date, expiration_date, strike, 
                            option_type=option_type, model='binomial')
    
    print(f"Deep {'ITM' if ((option_type == 'call' and strike_multiplier < 1) or (option_type == 'put' and strike_multiplier > 1)) else 'OTM'} "
          f"{option_type} ({date_str}, {days_to_expiry} days, S={current_price:.2f}, K={strike})")
    print(f"  Black-Scholes: ${bs_price:.2f}")
    print(f"  Binomial:      ${bin_price:.2f}")

def test_short_expiry(data, date_str, days_to_expiry):
    """Test very short expiration options"""
    current_date = datetime.strptime(date_str, '%Y-%m-%d')
    expiration_date = current_date + timedelta(days=days_to_expiry)
    
    if current_date < data['date'].min() or current_date > data['date'].max():
        print(f"Date {date_str} out of range, skipping test")
        return
        
    current_price_row = data[data['date'] <= current_date].iloc[-1]
    current_price = current_price_row['Adjusted']
    strike = round(current_price)
    
    bs_call = price_options('SPY', current_date, expiration_date, strike, option_type='call', model='black_scholes')
    bs_put = price_options('SPY', current_date, expiration_date, strike, option_type='put', model='black_scholes')
    
    print(f"Short-term ATM options ({date_str}, {days_to_expiry} days, S={current_price:.2f}, K={strike})")
    print(f"  Call (BS): ${bs_call:.2f}")
    print(f"  Put (BS):  ${bs_put:.2f}")

def test_long_expiry(data, date_str, days_to_expiry):
    """Test longer-term options"""
    current_date = datetime.strptime(date_str, '%Y-%m-%d')
    expiration_date = current_date + timedelta(days=days_to_expiry)
    
    if expiration_date > data['date'].max():
        print(f"Expiration date {expiration_date.strftime('%Y-%m-%d')} beyond data range, skipping test")
        return
        
    current_price_row = data[data['date'] <= current_date].iloc[-1]
    current_price = current_price_row['Adjusted']
    strike = round(current_price)
    
    bin_call = price_options('SPY', current_date, expiration_date, strike, option_type='call', model='binomial', steps=150)
    bin_put = price_options('SPY', current_date, expiration_date, strike, option_type='put', model='binomial', steps=150)
    
    print(f"Long-term ATM options ({date_str}, {days_to_expiry} days, S={current_price:.2f}, K={strike})")
    print(f"  Call (Binomial): ${bin_call:.2f}")
    print(f"  Put (Binomial):  ${bin_put:.2f}")

if __name__ == "__main__":
    main()
