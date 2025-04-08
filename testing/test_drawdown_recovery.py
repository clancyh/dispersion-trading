import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from backtester.risk_manager import RiskManager

def test_drawdown_recovery_watermark():
    """Test the drawdown recovery and watermark reset functionality"""
    
    # Create a test configuration
    config = {
        'portfolio': {
            'initial_cash': 1000000
        },
        'risk_management': {
            'max_portfolio_risk_pct': 0.2,
            'max_position_risk_pct': 0.05,
            'stop_loss_pct': 0.15,
            'max_drawdown_pct': 0.15,  # Lower threshold to test
            'risk_limits_enabled': True,
            'recovery_days_after_max_drawdown': 5,  # Shorter period for testing
            'recovery_percentage': 0.3  # Lower recovery requirement for testing
        }
    }
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    
    # Generate dates for testing
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(30)]
    
    # Create test portfolio values that:
    # 1. Start at initial value
    # 2. Rise to a peak
    # 3. Fall to trigger max drawdown
    # 4. Recover during cooling-off period but not enough
    # 5. Recover enough to exit recovery mode
    # 6. Rise to a new peak
    # 7. Fall again to test the new watermark
    values = [
        1000000,  # Initial value (day 0)
        1050000,  # Up 5% (day 1)
        1100000,  # New peak (day 2)
        1000000,  # Down 9.1% from peak (day 3)
        950000,   # Down 13.6% from peak (day 4)
        850000,   # Down 22.7% from peak - should trigger max drawdown (day 5)
        860000,   # Small recovery (day 6)
        870000,   # More recovery (day 7)
        880000,   # More recovery (day 8)
        890000,   # More recovery (day 9)
        900000,   # Enough recovery after cooling period (day 10)
        910000,   # Continue rising (day 11)
        920000,   # Continue rising (day 12)
        930000,   # New peak after reset (day 13)
        940000,   # New peak (day 14)
        950000,   # New peak (day 15)
        900000,   # Drop from new peak, but less than max DD (day 16)
        850000,   # Further drop, should trigger max DD from new watermark (day 17)
        860000,   # Small recovery (day 18)
        900000,   # Enough recovery after cooling period (day 23)
        925000,   # Continue rising (day 24)
        950000,   # New peak after second reset (day 25)
        960000,   # New peak (day 26)
        970000,   # New peak (day 27)
        980000,   # New peak (day 28)
        990000    # New peak (day 29)
    ]
    
    # Pad values to match dates length if needed
    if len(values) < len(dates):
        values.extend([values[-1]] * (len(dates) - len(values)))
    
    # Track results
    results = []
    
    # Process values with dates
    for i, (date, value) in enumerate(zip(dates, values)):
        within_limits = risk_manager.set_portfolio_value(value, date)
        
        # Print status
        drawdown_pct = risk_manager.current_drawdown * 100
        peak_value = risk_manager.peak_portfolio_value
        recovery_mode = risk_manager.recovery_mode
        
        result = {
            'date': date,
            'value': value,
            'peak_value': peak_value,
            'drawdown_pct': drawdown_pct,
            'recovery_mode': recovery_mode,
            'within_limits': within_limits,
        }
        
        # If in recovery mode, add recovery details
        if recovery_mode:
            days_in_recovery = (date - risk_manager.max_drawdown_date).days
            recovery_target = risk_manager.recovery_target_value
            recovery_progress = (value - risk_manager.max_drawdown_date_value) / (recovery_target - risk_manager.max_drawdown_date_value)
            days_remaining = max(0, risk_manager.recovery_days - days_in_recovery)
            
            result.update({
                'days_in_recovery': days_in_recovery,
                'recovery_target': recovery_target,
                'recovery_progress': recovery_progress,
                'days_remaining': days_remaining
            })
            
            print(f"Day {i}: Value: ${value:,.2f}, Peak: ${peak_value:,.2f}, Drawdown: {drawdown_pct:.2f}%, "
                  f"RECOVERY MODE (Day {days_in_recovery}/{risk_manager.recovery_days}) - "
                  f"Progress: {recovery_progress:.2%}, Target: ${recovery_target:,.2f}, "
                  f"Days remaining: {days_remaining}")
        else:
            print(f"Day {i}: Value: ${value:,.2f}, Peak: ${peak_value:,.2f}, Drawdown: {drawdown_pct:.2f}%, "
                  f"Within limits: {within_limits}")
        
        results.append(result)
    
    # Convert results to DataFrame
    results_df = pd.DataFrame(results)
    
    # Plot results
    plt.figure(figsize=(15, 12))
    
    # Plot 1: Portfolio Value and Peak Value
    plt.subplot(3, 1, 1)
    plt.plot(results_df['date'], results_df['value'], marker='o', label='Portfolio Value')
    plt.plot(results_df['date'], results_df['peak_value'], linestyle='--', color='green', label='Peak Value (Watermark)')
    plt.axhline(y=config['portfolio']['initial_cash'], color='gray', linestyle=':', label='Initial Cash')
    for i, row in results_df.iterrows():
        if row['recovery_mode']:
            plt.axvspan(row['date'], row['date'] + timedelta(days=1), alpha=0.2, color='red')
    plt.title('Portfolio Value and Peak Value (Watermark)')
    plt.ylabel('Value ($)')
    plt.legend()
    plt.grid(True)
    
    # Plot 2: Drawdown
    plt.subplot(3, 1, 2)
    plt.plot(results_df['date'], results_df['drawdown_pct'], marker='o', color='red', label='Drawdown')
    plt.axhline(y=config['risk_management']['max_drawdown_pct']*100, color='red', linestyle='--', 
                label=f"Max Drawdown ({config['risk_management']['max_drawdown_pct']*100}%)")
    for i, row in results_df.iterrows():
        if row['recovery_mode']:
            plt.axvspan(row['date'], row['date'] + timedelta(days=1), alpha=0.2, color='red')
    plt.title('Portfolio Drawdown')
    plt.ylabel('Drawdown (%)')
    plt.legend()
    plt.grid(True)
    
    # Plot 3: Recovery Mode details
    recovery_df = results_df[results_df['recovery_mode']]
    if not recovery_df.empty:
        plt.subplot(3, 1, 3)
        
        if 'recovery_progress' in recovery_df.columns:
            plt.plot(recovery_df['date'], recovery_df['recovery_progress']*100, marker='o', color='blue', label='Recovery Progress')
            plt.axhline(y=100, color='green', linestyle='--', label='Recovery Target (100%)')
            plt.title('Recovery Progress during Recovery Mode')
            plt.ylabel('Progress (%)')
            plt.legend()
            plt.grid(True)
    
    plt.tight_layout()
    
    # Create results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    plt.savefig('results/drawdown_recovery_test.png')
    print("\nPlot saved to results/drawdown_recovery_test.png")
    
    # Save data to CSV for analysis
    results_df.to_csv('results/drawdown_recovery_data.csv', index=False)
    print("Data saved to results/drawdown_recovery_data.csv")

if __name__ == "__main__":
    test_drawdown_recovery_watermark() 