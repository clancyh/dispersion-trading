import pandas as pd
import numpy as np
import scipy.stats

def calculate_performance_metrics(data_path="results/aligned_strategy_and_benchmark.csv", risk_free_rate=0.0, trading_days_per_year=252, var_confidence_level=0.95):
    """
    Calculates a comprehensive set of performance and risk metrics for a strategy
    and its benchmark.

    Args:
        data_path (str): Path to the CSV file containing 'date', 'portfolio_value', 
                         and 'spy_benchmark_value'.
        risk_free_rate (float): Annual risk-free rate for Sharpe and Alpha calculation.
        trading_days_per_year (int): Number of trading days in a year.
        var_confidence_level (float): Confidence level for VaR and CVaR (e.g., 0.95 for 95%).

    Returns:
        dict: A dictionary containing all calculated metrics.
    """
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"Error: Data file not found at {data_path}")
        return None

    if not {'date', 'portfolio_value', 'spy_benchmark_value'}.issubset(df.columns):
        print("Error: CSV must contain 'date', 'portfolio_value', and 'spy_benchmark_value' columns.")
        return None

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').set_index('date')

    # Calculate daily returns
    df['portfolio_returns'] = df['portfolio_value'].pct_change()
    df['benchmark_returns'] = df['spy_benchmark_value'].pct_change()
    
    # Drop the first row with NaN returns
    df_returns = df[['portfolio_returns', 'benchmark_returns']].dropna()

    portfolio_returns = df_returns['portfolio_returns']
    benchmark_returns = df_returns['benchmark_returns']

    metrics = {}

    # --- Metrics for Portfolio ---
    metrics['portfolio'] = {}
    metrics['portfolio']['cumulative_return'] = (portfolio_returns + 1).prod() - 1
    metrics['portfolio']['annualized_return'] = ((1 + portfolio_returns.mean()) ** trading_days_per_year) - 1
    metrics['portfolio']['annualized_volatility'] = portfolio_returns.std() * np.sqrt(trading_days_per_year)
    
    # Sharpe Ratio
    excess_returns_portfolio = portfolio_returns - (risk_free_rate / trading_days_per_year)
    if metrics['portfolio']['annualized_volatility'] == 0:
        metrics['portfolio']['sharpe_ratio'] = np.nan
    else:
        metrics['portfolio']['sharpe_ratio'] = (excess_returns_portfolio.mean() * trading_days_per_year) / metrics['portfolio']['annualized_volatility']

    # Sortino Ratio
    downside_returns_portfolio = portfolio_returns[portfolio_returns < 0]
    if len(downside_returns_portfolio) == 0 or downside_returns_portfolio.std() == 0 :
         metrics['portfolio']['sortino_ratio'] = np.nan
    else:
        downside_std_portfolio = downside_returns_portfolio.std() * np.sqrt(trading_days_per_year)
        if downside_std_portfolio == 0:
            metrics['portfolio']['sortino_ratio'] = np.nan # or infinity if mean excess return is positive
        else:
            metrics['portfolio']['sortino_ratio'] = (excess_returns_portfolio.mean() * trading_days_per_year) / downside_std_portfolio


    # Max Drawdown
    cumulative_returns_portfolio = (1 + portfolio_returns).cumprod()
    peak_portfolio = cumulative_returns_portfolio.expanding(min_periods=1).max()
    drawdown_portfolio = (cumulative_returns_portfolio - peak_portfolio) / peak_portfolio
    metrics['portfolio']['max_drawdown'] = drawdown_portfolio.min()
    
    # VaR (Historical)
    metrics['portfolio']['var_historical'] = -np.percentile(portfolio_returns, (1 - var_confidence_level) * 100)
    
    # CVaR (Historical)
    metrics['portfolio']['cvar_historical'] = -portfolio_returns[portfolio_returns <= -metrics['portfolio']['var_historical']].mean()


    # --- Metrics for Benchmark ---
    metrics['benchmark'] = {}
    metrics['benchmark']['cumulative_return'] = (benchmark_returns + 1).prod() - 1
    metrics['benchmark']['annualized_return'] = ((1 + benchmark_returns.mean()) ** trading_days_per_year) - 1
    metrics['benchmark']['annualized_volatility'] = benchmark_returns.std() * np.sqrt(trading_days_per_year)

    # Sharpe Ratio
    excess_returns_benchmark = benchmark_returns - (risk_free_rate / trading_days_per_year)
    if metrics['benchmark']['annualized_volatility'] == 0:
        metrics['benchmark']['sharpe_ratio'] = np.nan
    else:
        metrics['benchmark']['sharpe_ratio'] = (excess_returns_benchmark.mean() * trading_days_per_year) / metrics['benchmark']['annualized_volatility']
    
    # Sortino Ratio
    downside_returns_benchmark = benchmark_returns[benchmark_returns < 0]
    if len(downside_returns_benchmark) == 0 or downside_returns_benchmark.std() == 0:
        metrics['benchmark']['sortino_ratio'] = np.nan
    else:
        downside_std_benchmark = downside_returns_benchmark.std() * np.sqrt(trading_days_per_year)
        if downside_std_benchmark == 0:
            metrics['benchmark']['sortino_ratio'] = np.nan
        else:
            metrics['benchmark']['sortino_ratio'] = (excess_returns_benchmark.mean() * trading_days_per_year) / downside_std_benchmark


    # Max Drawdown
    cumulative_returns_benchmark = (1 + benchmark_returns).cumprod()
    peak_benchmark = cumulative_returns_benchmark.expanding(min_periods=1).max()
    drawdown_benchmark = (cumulative_returns_benchmark - peak_benchmark) / peak_benchmark
    metrics['benchmark']['max_drawdown'] = drawdown_benchmark.min()

    # VaR (Historical)
    metrics['benchmark']['var_historical'] = -np.percentile(benchmark_returns, (1 - var_confidence_level) * 100)
    
    # CVaR (Historical)
    metrics['benchmark']['cvar_historical'] = -benchmark_returns[benchmark_returns <= -metrics['benchmark']['var_historical']].mean()

    # --- Relative Metrics (Portfolio vs Benchmark) ---
    metrics['relative'] = {}
    
    # Beta
    covariance = portfolio_returns.cov(benchmark_returns)
    variance_benchmark = benchmark_returns.var()
    if variance_benchmark == 0:
        metrics['relative']['beta'] = np.nan
    else:
        metrics['relative']['beta'] = covariance / variance_benchmark
        
    # Alpha
    # Alpha = Portfolio Return - Risk-Free Rate - Beta * (Benchmark Return - Risk-Free Rate)
    # All annualized
    alpha_val = metrics['portfolio']['annualized_return'] - risk_free_rate - \
                metrics['relative']['beta'] * (metrics['benchmark']['annualized_return'] - risk_free_rate)
    metrics['relative']['alpha'] = alpha_val

    # Correlation
    metrics['relative']['correlation'] = portfolio_returns.corr(benchmark_returns)
    
    # Information Ratio
    # (Portfolio Return - Benchmark Return) / Tracking Error
    # Tracking Error is std of (Portfolio Return - Benchmark Return)
    active_returns = portfolio_returns - benchmark_returns
    tracking_error = active_returns.std() * np.sqrt(trading_days_per_year)
    if tracking_error == 0 or np.isnan(tracking_error):
        metrics['relative']['information_ratio'] = np.nan
    else:
        metrics['relative']['information_ratio'] = (active_returns.mean() * trading_days_per_year) / tracking_error
        
    return metrics

def print_and_save_metrics(metrics, output_path="performance/scripts/full_performance_analysis.txt", var_confidence_level=0.95):
    if metrics is None:
        return

    report = "\\n--- Performance Analysis Report ---\\n"
    report += f"Risk-Free Rate Assumed: {metrics.get('risk_free_rate', 0.0):.2%}\\n"
    report += f"Trading Days Per Year: {metrics.get('trading_days_per_year', 252)}\\n"
    report += f"VaR/CVaR Confidence Level: {var_confidence_level:.0%}\\n"

    metrics_to_percentage = ['cumulative_return', 'annualized_return', 'annualized_volatility', 'max_drawdown', 'var_historical', 'cvar_historical']

    report += "\\n--- Portfolio Metrics ---\\n"
    for key, value in metrics['portfolio'].items():
        if np.isnan(value):
            report += f"{key.replace('_', ' ').title()}: NaN\\n"
        elif key in metrics_to_percentage:
            report += f"{key.replace('_', ' ').title()}: {value*100:.2f}%\\n"
        else: # sharpe_ratio, sortino_ratio
            report += f"{key.replace('_', ' ').title()}: {value:.4f}\\n"
        
    report += "\\n--- Benchmark Metrics ---\\n"
    for key, value in metrics['benchmark'].items():
        if np.isnan(value):
            report += f"{key.replace('_', ' ').title()}: NaN\\n"
        elif key in metrics_to_percentage:
            report += f"{key.replace('_', ' ').title()}: {value*100:.2f}%\\n"
        else: # sharpe_ratio, sortino_ratio
            report += f"{key.replace('_', ' ').title()}: {value:.4f}\\n"

    report += "\\n--- Relative Metrics (Portfolio vs Benchmark) ---\n"
    for key, value in metrics['relative'].items():
        if np.isnan(value):
            report += f"{key.replace('_', ' ').title()}: NaN\\n"
        elif key == 'alpha': # Alpha is usually expressed as percentage (annualized)
            report += f"{key.replace('_', ' ').title()}: {value*100:.2f}% (annualized)\\n"
        else: # beta, correlation, information_ratio
            report += f"{key.replace('_', ' ').title()}: {value:.4f}\\n"

    print(report)
    try:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"\\nMetrics saved to {output_path}")
    except IOError:
        print(f"Error: Could not write metrics to {output_path}")


if __name__ == "__main__":
    # Configuration
    DATA_FILE_PATH = "results/aligned_strategy_and_benchmark.csv" # Corrected path
    RISK_FREE_RATE = 0.00 # Assuming 0% risk-free rate
    TRADING_DAYS_PER_YEAR = 252
    VAR_CVAR_CONFIDENCE = 0.95

    calculated_metrics = calculate_performance_metrics(
        data_path=DATA_FILE_PATH,
        risk_free_rate=RISK_FREE_RATE,
        trading_days_per_year=TRADING_DAYS_PER_YEAR,
        var_confidence_level=VAR_CVAR_CONFIDENCE
    )
    
    if calculated_metrics:
        # Add config to metrics dict for saving
        calculated_metrics['risk_free_rate'] = RISK_FREE_RATE
        calculated_metrics['trading_days_per_year'] = TRADING_DAYS_PER_YEAR
        print_and_save_metrics(calculated_metrics, var_confidence_level=VAR_CVAR_CONFIDENCE) 