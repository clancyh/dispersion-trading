import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from backtester.engine import BacktestEngine
from backtester.logger import BacktestLogger

def main():
    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Create results directory if it doesn't exist
    os.makedirs(config['paths']['results_dir'], exist_ok=True)
    
    # Initialize logger for main program
    logger = BacktestLogger(config)
    
    # Display initial configuration
    debug_mode = config.get('logging', {}).get('debug_mode', False)
    if debug_mode:
        logger.debug("Running backtest with the following configuration:")
        logger.debug(f"Date Range: {config['backtest']['start_date']} to {config['backtest']['end_date']}")
        logger.debug(f"Initial Cash: ${config['portfolio']['initial_cash']:,.2f}")
        logger.debug(f"Index: {config['universe']['index']}")
        logger.debug(f"Number of Stocks: {config['universe']['num_stocks']}")
        logger.debug(f"Risk Config: max drawdown {config['risk_management']['max_drawdown_pct']:.1%}, " +
                    f"stop loss {config['risk_management']['stop_loss_pct']:.1%}")
    else:
        logger.info(f"Running backtest from {config['backtest']['start_date']} to {config['backtest']['end_date']}")
    
    # Initialize and run the backtest
    engine = BacktestEngine(config)
    results = engine.run()
    
    # Display performance metrics
    metrics = results['performance_metrics']
    logger.info("\n" + "="*30)
    logger.info("BACKTEST RESULTS")
    logger.info("="*30)
    logger.info(f"Total Return: {metrics['total_return']:.2%}")
    logger.info(f"Annualized Return: {metrics['annualized_return']:.2%}")
    logger.info(f"Annualized Volatility: {metrics['annualized_volatility']:.2%}")
    logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
    logger.info(f"Final Portfolio Value: ${metrics['final_value']:,.2f}")
    
    # Display risk metrics if in debug mode
    if debug_mode:
        logger.debug("\nDetailed Risk Metrics:")
        logger.debug(f"Average Exposure: {metrics.get('avg_exposure', 0):.2%} of portfolio")
        logger.debug(f"Maximum Exposure: {metrics.get('max_exposure', 0):.2%} of portfolio")
        logger.debug(f"Max Allowed Drawdown: {config['risk_management']['max_drawdown_pct']:.2%}")
        logger.debug(f"Stop-Loss Level: {config['risk_management']['stop_loss_pct']:.2%}")
    
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
        f.write(f"Max Drawdown: {metrics['max_drawdown']:.2%}\n\n")
        f.write("Risk Management Settings:\n")
        f.write(f"Position Sizing Method: {config['risk_management']['position_sizing_method']}\n")
        f.write(f"Max Portfolio Risk: {config['risk_management']['max_portfolio_risk_pct']:.2%}\n")
        f.write(f"Max Position Risk: {config['risk_management']['max_position_risk_pct']:.2%}\n")
        f.write(f"Stop-Loss Level: {config['risk_management']['stop_loss_pct']:.2%}\n")
        f.write(f"Max Drawdown Limit: {config['risk_management']['max_drawdown_pct']:.2%}\n")
    
    logger.info(f"Results saved to {results_dir}")

if __name__ == "__main__":
    main()
