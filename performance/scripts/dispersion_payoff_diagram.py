import numpy as np
import matplotlib.pyplot as plt

# Generate data points for the payoff diagram
spread = np.linspace(-5, 5, 1000)  # Spread range from -5% to 5%

# Long dispersion trade payoff
# Buy single-stock options, sell index options
# Profits when spread is wide (low correlation)
long_dispersion = np.abs(spread) - 2  # Profits as spread widens

# Short dispersion trade payoff
# Sell single-stock options, buy index options
# Profits when spread is narrow (high correlation)
short_dispersion = -np.abs(spread) + 2  # Profits as spread narrows

# Create the plot
plt.figure(figsize=(12, 8))
plt.plot(spread, long_dispersion, 'b-', label='Long Dispersion (Bet on Low Correlation)', linewidth=2)
plt.plot(spread, short_dispersion, 'r-', label='Short Dispersion (Bet on High Correlation)', linewidth=2)

# Add horizontal and vertical lines at zero
plt.axhline(y=0, color='k', linestyle='--', alpha=0.3)
plt.axvline(x=0, color='k', linestyle='--', alpha=0.3)

# Customize the plot
plt.title('Dispersion Trading Payoff Diagram', fontsize=14, pad=20)
plt.xlabel('Index vs Single-Stock Volatility Spread (%)', fontsize=12)
plt.ylabel('Profit/Loss', fontsize=12)
plt.grid(True, alpha=0.3)
plt.legend(fontsize=12)

# Add detailed annotations
plt.annotate('Profit Zone\n(Spread Widens, Low Correlation)', xy=(4, 2), xytext=(3, 2.5),
            arrowprops=dict(facecolor='blue', shrink=0.05), color='blue')
plt.annotate('Profit Zone\n(Spread Narrows, High Correlation)', xy=(0, 2), xytext=(-2, 2.5),
            arrowprops=dict(facecolor='red', shrink=0.05), color='red')

# Add explanation text
explanation = (
    "Spread = Index Implied Vol - Weighted Avg Single-Stock Implied Vol\n"
    "Positive Spread: Index IV > Single-Stock IV\n"
    "Negative Spread: Index IV < Single-Stock IV"
)
plt.figtext(0.5, 0.01, explanation, ha='center', fontsize=10, 
            bbox=dict(facecolor='white', alpha=0.8))

# Adjust layout and display
plt.tight_layout()
plt.subplots_adjust(bottom=0.15)  # Make room for the explanation text
plt.savefig('dispersion_payoff_diagram.png', dpi=300, bbox_inches='tight')
plt.close() 