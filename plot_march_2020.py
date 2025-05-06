import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# Read the portfolio history data
df = pd.read_csv('results/portfolio_history.csv')
spy_df = pd.read_csv('data/processed/SPY.csv')

# Convert date columns to datetime
df['date'] = pd.to_datetime(df['date'])
spy_df['date'] = pd.to_datetime(spy_df['date'])

# Filter for March 2020
march_2020 = df[(df['date'] >= '2020-03-01') & (df['date'] <= '2020-03-31')]
spy_march_2020 = spy_df[(spy_df['date'] >= '2020-03-01') & (spy_df['date'] <= '2020-03-31')]

# Calculate theoretical SPY investment
initial_value = march_2020['value'].iloc[0]
spy_initial_price = spy_march_2020['Close'].iloc[0]
spy_shares = initial_value / spy_initial_price
spy_march_2020['theoretical_value'] = spy_march_2020['Close'] * spy_shares

# Create a figure with multiple subplots
fig, axes = plt.subplots(3, 1, figsize=(12, 15), sharex=True)
fig.suptitle('Portfolio Performance vs SPY - March 2020', fontsize=16)

# Plot 1: Portfolio Value vs SPY
axes[0].plot(march_2020['date'], march_2020['value'], label='Portfolio Value', color='blue', linewidth=2)
axes[0].plot(spy_march_2020['date'], spy_march_2020['theoretical_value'], label='SPY Equivalent', color='red', linewidth=2, linestyle='--')
axes[0].set_ylabel('Value ($)')
axes[0].set_title('Portfolio Value vs SPY Investment')
axes[0].legend()
axes[0].grid(True)

# Plot 2: Drawdown
axes[1].fill_between(march_2020['date'], march_2020['drawdown'], 0, color='red', alpha=0.3)
axes[1].plot(march_2020['date'], march_2020['drawdown'], color='red', linewidth=2)
axes[1].set_ylabel('Drawdown')
axes[1].set_title('Portfolio Drawdown')
axes[1].grid(True)
axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))

# Plot 3: Daily Returns
axes[2].bar(march_2020['date'], march_2020['return'], color='blue', alpha=0.7)
axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
axes[2].set_ylabel('Daily Return')
axes[2].set_title('Daily Returns')
axes[2].grid(True)
axes[2].yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))

# Format x-axis to show dates nicely
for ax in axes:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))

# Calculate performance metrics for both portfolio and SPY
portfolio_end_value = march_2020['value'].iloc[-1]
spy_end_value = spy_march_2020['theoretical_value'].iloc[-1]
portfolio_return = (portfolio_end_value - initial_value) / initial_value
spy_return = (spy_end_value - initial_value) / initial_value

summary_text = f"March 2020 Performance Summary:\n"
summary_text += f"Starting Value: ${initial_value:,.2f}\n"
summary_text += f"Portfolio Ending Value: ${portfolio_end_value:,.2f}\n"
summary_text += f"SPY Ending Value: ${spy_end_value:,.2f}\n"
summary_text += f"Portfolio Return: {portfolio_return:.2%}\n"
summary_text += f"SPY Return: {spy_return:.2%}\n"
summary_text += f"Relative Outperformance: {(portfolio_return - spy_return):.2%}"

fig.text(0.15, 0.02, summary_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.8))

# Adjust layout and save the figure
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.savefig('march_2020_performance.png', dpi=300)
plt.show()

# Print the summary to console
print(summary_text) 