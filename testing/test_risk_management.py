import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add the project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from backtester.risk_manager import RiskManager

def test_risk_manager_basic():
    """Test the basic functionality of the RiskManager class"""
    
    # Create a test configuration
    config = {
        'portfolio': {
            'initial_cash': 1000000
        },
        'risk_management': {
            'max_portfolio_risk_pct': 0.2,
            'max_position_risk_pct': 0.05,
            'stop_loss_pct': 0.15,
            'max_drawdown_pct': 0.25,
            'risk_limits_enabled': True
        }
    }
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    
    # Test portfolio value tracking and drawdown calculation
    values = [
        1000000,  # Initial value
        1050000,  # Up 5%
        1100000,  # New peak
        1050000,  # Down from peak -> 4.5% drawdown
        1000000,  # Down further -> 9.1% drawdown
        900000,   # Down further -> 18.2% drawdown 
        800000,   # Exceeds 25% drawdown -> should trigger
    ]
    
    drawdowns = []
    limit_breaches = []
    
    for i, value in enumerate(values):
        within_limits = risk_manager.set_portfolio_value(value)
        drawdowns.append(risk_manager.current_drawdown)
        limit_breaches.append(not within_limits)
        
        print(f"Portfolio value: ${value:,.2f}, Drawdown: {risk_manager.current_drawdown:.2%}, Within limits: {within_limits}")
    
    # Test stop-loss detection
    position_long = {
        'ticker': 'SPY',
        'option_type': 'call',
        'entry_value': 10000,
        'current_value': 8000  # 20% loss
    }
    
    position_short = {
        'ticker': 'SPY',
        'option_type': 'put',
        'entry_value': -10000,  # negative for short positions
        'current_value': -12000  # 20% loss on short
    }
    
    stop_loss_long = risk_manager.check_position_stop_loss(position_long)
    stop_loss_short = risk_manager.check_position_stop_loss(position_short)
    
    print(f"Long position stop-loss triggered: {stop_loss_long}")
    print(f"Short position stop-loss triggered: {stop_loss_short}")
    
    # Test position sizing
    for price in [1.0, 5.0, 10.0, 50.0, 100.0]:
        contracts = risk_manager.calculate_position_sizing('dispersion', 'SPY', 'call', price, 1000000)
        print(f"Option price: ${price:.2f}, Contracts: {contracts}, Total value: ${contracts * price * 100:,.2f}")
    
    # Test portfolio risk limit
    for position_value in [50000, 150000, 250000, 350000]:
        within_risk = risk_manager.check_portfolio_risk(position_value, 1000000)
        print(f"Position value: ${position_value:,.2f}, Within risk limits: {within_risk}")
    
    # Plot drawdown
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    plt.plot(values, marker='o')
    plt.axhline(y=values[2], color='g', linestyle='--', label='Peak value')
    plt.title('Portfolio Value')
    plt.grid(True)
    
    plt.subplot(2, 1, 2)
    plt.plot(drawdowns, marker='o')
    plt.axhline(y=config['risk_management']['max_drawdown_pct'], color='r', linestyle='--', label='Max drawdown')
    for i, breach in enumerate(limit_breaches):
        if breach:
            plt.plot(i, drawdowns[i], 'ro', markersize=10)
    plt.title('Drawdown')
    plt.grid(True)
    
    plt.tight_layout()
    
    # Create results directory if it doesn't exist
    os.makedirs('results', exist_ok=True)
    plt.savefig('results/risk_management_test.png')
    print("\nPlot saved to results/risk_management_test.png")

def test_risk_manager_kelly():
    """Test the Kelly criterion position sizing function"""
    
    # Create a test configuration with Kelly position sizing
    config = {
        'portfolio': {
            'initial_cash': 1000000
        },
        'risk_management': {
            'max_portfolio_risk_pct': 0.2,
            'max_position_risk_pct': 0.05,
            'stop_loss_pct': 0.15,
            'max_drawdown_pct': 0.25,
            'position_sizing_method': 'kelly',
            'risk_limits_enabled': True
        }
    }
    
    # Initialize risk manager
    risk_manager = RiskManager(config)
    
    # Test position sizing with Kelly criterion for different option prices
    option_prices = [1.0, 5.0, 10.0, 25.0, 50.0, 100.0]
    portfolio_values = [100000, 500000, 1000000, 5000000]
    
    for portfolio_value in portfolio_values:
        contracts = []
        for price in option_prices:
            contract_count = risk_manager.calculate_position_sizing('dispersion', 'SPY', 'call', price, portfolio_value)
            contracts.append(contract_count)
            
        plt.figure(figsize=(10, 6))
        plt.bar(option_prices, contracts)
        plt.title(f'Position Sizing with Kelly Criterion (Portfolio: ${portfolio_value:,.0f})')
        plt.xlabel('Option Price ($)')
        plt.ylabel('Number of Contracts')
        plt.grid(True, axis='y')
        
        # Create results directory if it doesn't exist
        os.makedirs('results', exist_ok=True)
        plt.savefig(f'results/kelly_sizing_{portfolio_value}.png')
        
    print("\nKelly position sizing plots saved to results/")

if __name__ == "__main__":
    print("Testing basic risk management functionality...")
    test_risk_manager_basic()
    
    print("\nTesting Kelly criterion position sizing...")
    test_risk_manager_kelly() 