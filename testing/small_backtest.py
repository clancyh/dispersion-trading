import sys
import os
import json
from datetime import datetime, timedelta
import pandas as pd

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from backtester.risk_manager import RiskManager

def test_recovery_in_backtest():
    """
    Create a simple backtest-like scenario to test recovery mode
    """
    # Create a test configuration
    config = {
        'portfolio': {
            'initial_cash': 1000000
        },
        'risk_management': {
            'max_portfolio_risk_pct': 0.2,
            'max_position_risk_pct': 0.05,
            'stop_loss_pct': 0.15,
            'max_drawdown_pct': 0.15,  # Set to match the actual config
            'risk_limits_enabled': True,
            'recovery_days_after_max_drawdown': 10,  # Set to match the actual config
            'recovery_percentage': 0.5  # Set to match the actual config
        }
    }
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    
    # Create a sequence of dates
    start_date = datetime(2021, 1, 1)
    dates = []
    values = []
    
    # Create 60 trading days (about 3 months)
    for i in range(60):
        # Skip weekends
        if i % 7 == 5 or i % 7 == 6:
            continue
        dates.append(start_date + timedelta(days=i))
    
    # Generate a portfolio value sequence
    # 1. Starts at 1M
    # 2. Grows to 1.1M
    # 3. Drops to trigger max drawdown
    # 4. Recovers slowly
    
    # First 20 days: Growth
    current_value = 1000000
    for i in range(20):
        if i < len(dates):
            # Some days are up, some down, but overall growing
            change = 0.005 * (1 if i % 5 != 0 else -0.5)
            current_value *= (1 + change)
            values.append(current_value)
    
    # Peak value should be around 1.05M
    
    # Next 10 days: Big drop to trigger drawdown
    for i in range(10):
        if i + 20 < len(dates):
            # Big daily drops
            current_value *= 0.975
            values.append(current_value)
    
    # Value should now be about 0.78M, well below max drawdown
    
    # Next 30 days: Slow recovery
    for i in range(30):
        if i + 30 < len(dates):
            # Small daily gains
            current_value *= 1.01
            values.append(current_value)
    
    # Run the backtest-like simulation
    print("\nRunning simulated backtest with controlled portfolio values...")
    
    peak_value = None
    drawdown_date = None
    recovery_target = None
    
    for i, (date, value) in enumerate(zip(dates, values)):
        # Update risk manager
        within_limits = risk_manager.set_portfolio_value(value, date)
        
        # Keep track of key values for analysis
        if i == 0 or value > peak_value:
            peak_value = value
        
        if risk_manager.recovery_mode and drawdown_date is None:
            drawdown_date = date
            recovery_target = risk_manager.recovery_target_value
    
    # Print summary
    print("\nSimulation Summary:")
    print(f"Start Date: {dates[0]}")
    print(f"End Date: {dates[-1]}")
    print(f"Start Value: ${values[0]:,.2f}")
    print(f"Peak Value: ${peak_value:,.2f}")
    print(f"Final Value: ${values[-1]:,.2f}")
    
    if drawdown_date:
        print(f"Drawdown Date: {drawdown_date}")
        print(f"Recovery Target: ${recovery_target:,.2f}")
        print(f"Days in simulation after drawdown: {(dates[-1] - drawdown_date).days}")
        
        # Calculate expected recovery
        drawdown_index = dates.index(drawdown_date)
        drawdown_value = values[drawdown_index]
        final_recovery_progress = (values[-1] - drawdown_value) / (recovery_target - drawdown_value)
        
        print(f"Final Recovery Progress: {final_recovery_progress:.2%}")
        print(f"Should have recovered: {'Yes' if final_recovery_progress >= 1.0 else 'No'}")
        print(f"Final Recovery Mode: {'Active' if risk_manager.recovery_mode else 'Exited'}")
    else:
        print("Never entered recovery mode")

if __name__ == "__main__":
    test_recovery_in_backtest() 