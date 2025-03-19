import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from backtester.engine import BacktestEngine

def main():
    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Create results directory if it doesn't exist
    os.makedirs(config['paths']['results_dir'], exist_ok=True)
    
    # Initialize and run the backtest
    engine = BacktestEngine(config)
    results = engine.run()
    
    # Display performance metrics
    metrics = results['performance_metrics']
    print("\nPerformance Metrics:")
    print(f"Total Return: {metrics['total_return']:.2%}")
    print(f"Annualized Return: {metrics['annualized_return']:.2%}")
    print(f"Annualized Volatility: {metrics['annualized_volatility']:.2%}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"Final Portfolio Value: ${metrics['final_value']:.2f}")
    
    # Plot results
    engine.plot_results()
    
    # Save detailed results
    results_dir = config['paths']['results_dir']
    results['portfolio_history'].to_csv(f"{results_dir}/portfolio_history.csv", index=False)
    results['trade_history'].to_csv(f"{results_dir}/trade_history.csv", index=False)
    
    # Save a summary report
    with open(f"{results_dir}/summary.txt", 'w') as f:
        f.write("Backtest Summary\n")
        f.write("===============\n\n")
        f.write(f"Start Date: {config['backtest']['start_date']}\n")
        f.write(f"End Date: {config['backtest']['end_date']}\n")
        f.write(f"Initial Capital: ${config['portfolio']['initial_cash']}\n")
        f.write(f"Final Capital: ${metrics['final_value']:.2f}\n\n")
        f.write("Performance Metrics:\n")
        f.write(f"Total Return: {metrics['total_return']:.2%}\n")
        f.write(f"Annualized Return: {metrics['annualized_return']:.2%}\n")
        f.write(f"Annualized Volatility: {metrics['annualized_volatility']:.2%}\n")
        f.write(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n")
        f.write(f"Max Drawdown: {metrics['max_drawdown']:.2%}\n")
    
    print(f"\nResults saved to {results_dir}")

if __name__ == "__main__":
    main()
