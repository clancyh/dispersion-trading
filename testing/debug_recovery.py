import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import json

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from backtester.risk_manager import RiskManager

def debug_recovery_calculation():
    """Test the recovery progress calculation specifically"""
    
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
    
    # Create a peak, then a drawdown scenario
    start_date = datetime(2021, 1, 1)
    
    # Day 1-10: Portfolio grows to peak
    print("\nPhase 1: Portfolio growth to peak")
    value = 1000000
    for i in range(10):
        current_date = start_date + timedelta(days=i)
        value = value * 1.01  # 1% growth each day
        within_limits = risk_manager.set_portfolio_value(value, current_date)
        print(f"Day {i+1}: {current_date.strftime('%Y-%m-%d')} Value: ${value:.2f}, Peak: ${risk_manager.peak_portfolio_value:.2f}, Drawdown: {risk_manager.current_drawdown:.2%}")
    
    # Record the peak value
    peak_value = risk_manager.peak_portfolio_value
    print(f"\nPeak portfolio value: ${peak_value:.2f}")
    
    # Initialize variables for drawdown tracking
    drawdown_value = None
    drawdown_date = None
    drawdown_amount = None
    recovery_amount = None
    recovery_target = None
    
    # Day 11-15: Portfolio drops to trigger max drawdown
    print("\nPhase 2: Portfolio decline to max drawdown")
    for i in range(5):
        current_date = start_date + timedelta(days=10+i)
        value = value * 0.96  # 4% drop each day
        within_limits = risk_manager.set_portfolio_value(value, current_date)
        print(f"Day {i+11}: {current_date.strftime('%Y-%m-%d')} Value: ${value:.2f}, Peak: ${risk_manager.peak_portfolio_value:.2f}, Drawdown: {risk_manager.current_drawdown:.2%}, In Recovery Mode: {risk_manager.recovery_mode}")
        
        # If we just entered recovery mode, record the details
        if risk_manager.recovery_mode and drawdown_value is None:
            drawdown_value = value
            drawdown_date = current_date
            drawdown_amount = peak_value - value
            recovery_amount = drawdown_amount * risk_manager.recovery_pct
            recovery_target = value + recovery_amount
            
            print(f"\nEntered recovery mode:")
            print(f"  Max Drawdown Date Value: ${risk_manager.max_drawdown_date_value:.2f}")
            print(f"  Recovery Target Value: ${risk_manager.recovery_target_value:.2f}")
            print(f"  Recovery Amount Needed: ${recovery_amount:.2f} ({risk_manager.recovery_pct:.0%} of ${drawdown_amount:.2f})")
    
    # Check if we entered recovery mode
    if drawdown_value is None:
        print("\nERROR: Did not enter recovery mode. Try adjusting the drawdown rate or max_drawdown_pct.")
        return
    
    # Day 16-25: Test different recovery scenarios
    print("\nPhase 3: Testing recovery progress with various portfolio values")
    
    # Calculate some test values
    test_values = [
        drawdown_value,  # Same as drawdown (0% recovery)
        drawdown_value + recovery_amount * 0.25,  # 25% recovery
        drawdown_value + recovery_amount * 0.5,   # 50% recovery
        drawdown_value + recovery_amount * 0.75,  # 75% recovery
        drawdown_value + recovery_amount,         # 100% recovery
        drawdown_value + recovery_amount * 1.1    # 110% recovery (above target)
    ]
    
    # Reset risk manager to recovery mode state to test with different values
    risk_manager.recovery_mode = True
    risk_manager.max_drawdown_date = drawdown_date
    risk_manager.max_drawdown_date_value = drawdown_value
    risk_manager.recovery_target_value = recovery_target
    
    # Test each value both during and after recovery period
    for i, test_value in enumerate(test_values):
        # During recovery period
        current_date = drawdown_date + timedelta(days=i+1)
        within_limits = risk_manager.set_portfolio_value(test_value, current_date)
        
        # Calculate and print the expected recovery progress
        expected_progress = (test_value - drawdown_value) / recovery_amount
        
        print(f"\nTest {i+1}: Value ${test_value:.2f} (Day {i+1} after drawdown)")
        print(f"  Expected Recovery Progress: {expected_progress:.2%}")
        
        # Verify that the recovery progress is calculated correctly
        if risk_manager.recovery_mode:
            recovery_progress = (test_value - risk_manager.max_drawdown_date_value) / (risk_manager.recovery_target_value - risk_manager.max_drawdown_date_value)
            print(f"  Manual Recovery Progress Calculation: {recovery_progress:.2%}")
            if abs(recovery_progress - expected_progress) > 0.01:
                print(f"  *** DISCREPANCY DETECTED: Expected {expected_progress:.2%} but calculated {recovery_progress:.2%}")
        else:
            print(f"  *** EXITED RECOVERY MODE at value ${test_value:.2f}")
    
    # Reset risk manager to recovery mode state again for the time test
    risk_manager.recovery_mode = True
    risk_manager.max_drawdown_date = drawdown_date
    risk_manager.max_drawdown_date_value = drawdown_value
    risk_manager.recovery_target_value = recovery_target
    
    # Test after recovery period elapses
    print("\nPhase 4: Testing recovery after time period elapses")
    for i, test_value in enumerate(test_values):
        # After recovery period
        current_date = drawdown_date + timedelta(days=risk_manager.recovery_days + i + 1)
        days_since_drawdown = (current_date - drawdown_date).days
        
        within_limits = risk_manager.set_portfolio_value(test_value, current_date)
        
        print(f"\nTest {i+1}: Value ${test_value:.2f} (Day {days_since_drawdown} after drawdown - AFTER RECOVERY PERIOD)")
        print(f"  Expected Recovery Progress: {((test_value - drawdown_value) / recovery_amount):.2%}")
        print(f"  Actual Status: Recovery Mode = {risk_manager.recovery_mode}")
        
        # If we exited recovery mode, print details
        if not risk_manager.recovery_mode:
            print(f"  *** EXITED RECOVERY MODE at value ${test_value:.2f}")
            print(f"  New Peak Value: ${risk_manager.peak_portfolio_value:.2f}")
        else:
            recovery_progress = (test_value - risk_manager.max_drawdown_date_value) / (risk_manager.recovery_target_value - risk_manager.max_drawdown_date_value)
            print(f"  Manual Recovery Progress Calculation: {recovery_progress:.2%}")

if __name__ == "__main__":
    debug_recovery_calculation() 