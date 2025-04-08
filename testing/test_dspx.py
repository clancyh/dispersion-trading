import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from backtester.dspx import load_dspx_data, calculate_dspx_signal

def test_dspx_signals():
    """Test the DSPX signal generation functionality"""
    # Load DSPX data
    print("Loading DSPX data...")
    dspx_data = load_dspx_data()
    
    # Plot DSPX historical values
    print(f"DSPX data ranges from {dspx_data['date'].min()} to {dspx_data['date'].max()}")
    print(f"Total data points: {len(dspx_data)}")
    
    # Test signal generation on a date range
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2021, 1, 1)
    
    print(f"\nTesting signal generation from {start_date.date()} to {end_date.date()}")
    
    # Create date range
    current_date = start_date
    signals = []
    
    # Parameters
    lookback = 30
    entry_threshold = 1.5
    exit_threshold = 0.5
    
    # Generate signals for each date
    while current_date <= end_date:
        try:
            signal = calculate_dspx_signal(
                dspx_data, 
                current_date, 
                lookback=lookback,
                entry_threshold=entry_threshold,
                exit_threshold=exit_threshold
            )
            
            if signal:
                print(f"Date: {current_date.date()}, Signal: {signal['signal']}, DSPX: {signal['metrics']['dspx_value']:.2f}, Z-Score: {signal['metrics']['z_score']:.2f}")
                signals.append({
                    'date': current_date.date(),
                    'signal': signal['signal'],
                    'dspx_value': signal['metrics']['dspx_value'],
                    'z_score': signal['metrics']['z_score']
                })
        except Exception as e:
            print(f"Error on {current_date.date()}: {str(e)}")
            
        # Move to next date
        current_date += timedelta(days=1)
    
    # Create a results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    
    # Plot the DSPX value and signals
    if signals:
        df_signals = pd.DataFrame(signals)
        
        # Filter DSPX data to the date range
        dspx_subset = dspx_data[(dspx_data['date'] >= start_date) & 
                               (dspx_data['date'] <= end_date)].copy()
        
        # Plot DSPX with signals
        plt.figure(figsize=(12, 8))
        
        # Plot DSPX values
        plt.plot(dspx_subset['date'], dspx_subset['DSPX'], label='DSPX Index')
        
        # Plot signals
        dispersion_signals = df_signals[df_signals['signal'] == 'ENTER_DISPERSION']
        reverse_signals = df_signals[df_signals['signal'] == 'ENTER_REVERSE_DISPERSION']
        exit_signals = df_signals[df_signals['signal'] == 'EXIT']
        
        if not dispersion_signals.empty:
            plt.scatter(
                dispersion_signals['date'], 
                dispersion_signals['dspx_value'],
                marker='^', color='green', s=100, label='Enter Dispersion'
            )
            
        if not reverse_signals.empty:
            plt.scatter(
                reverse_signals['date'], 
                reverse_signals['dspx_value'],
                marker='v', color='red', s=100, label='Enter Reverse Dispersion'
            )
            
        if not exit_signals.empty:
            plt.scatter(
                exit_signals['date'], 
                exit_signals['dspx_value'],
                marker='o', color='blue', s=100, label='Exit'
            )
        
        plt.title(f'DSPX Index and Signals (Entry Threshold: {entry_threshold}, Exit Threshold: {exit_threshold})')
        plt.xlabel('Date')
        plt.ylabel('DSPX Value')
        plt.legend()
        plt.grid(True)
        
        # Save the plot
        plt.savefig('results/dspx_signals.png')
        print("\nPlot saved to results/dspx_signals.png")

if __name__ == "__main__":
    test_dspx_signals() 