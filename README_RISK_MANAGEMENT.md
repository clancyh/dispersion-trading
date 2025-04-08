# Risk Management in Dispersion Trading

This document describes the risk management features implemented in the dispersion trading strategy system.

## Overview

The dispersion trading strategy involves trading index options versus component options based on observed disparities between implied and realized correlation. This type of trading strategy can be subject to significant risks, including:

1. Substantial losses during market dislocations
2. Excessive position sizes leading to outsized impacts
3. Drawdowns that compound over time

To mitigate these risks, we've implemented a comprehensive risk management system.

## Risk Management Features

### 1. Position Sizing Controls

- **Max Position Risk**: Limits the maximum risk exposure for any single position (default: 3% of portfolio)
- **Position Sizing Methods**:
  - `equal_risk`: Allocates the same dollar risk amount to each position
  - `kelly`: Uses a simplified Kelly criterion approach for optimal position sizing
- **Portfolio-Level Risk Limit**: Caps the total portfolio risk exposure (default: 15%)

### 2. Stop-Loss Mechanisms

- **Individual Position Stop-Loss**: Automatically closes positions that exceed a specified loss threshold (default: 10%)
- **Position Monitoring**: Tracks P&L for both long and short positions

### 3. Drawdown Protection

- **Maximum Drawdown Limit**: Forces closure of all positions if the portfolio drawdown exceeds a specified threshold (default: 15%)
- **Portfolio Value Monitoring**: Tracks historical peak portfolio value to calculate current drawdown

### 4. Trade Balance Controls

- **Balanced Exposure**: Ensures that long and short exposures in dispersion trades are properly balanced
- **Premium-Based Component Sizing**: Limits component option purchases based on the premium collected from index options
- **Long-Short Balance Factor**: Controls the ratio of component budget to premium collected (default: 0.9)
- **Maximum Long-Short Ratio**: Sets a maximum allowed ratio between long and short exposures (default: 1.1)

## Configuration Parameters

The risk management system can be configured through the `risk_management` section in the `config.json` file:

```json
"risk_management": {
  "max_portfolio_risk_pct": 0.15,
  "max_position_risk_pct": 0.03,
  "stop_loss_pct": 0.10,
  "max_drawdown_pct": 0.15,
  "max_options_vega_exposure": 25000,
  "max_options_theta_per_day": -2500,
  "position_sizing_method": "equal_risk",
  "risk_limits_enabled": true,
  "recovery_days_after_max_drawdown": 10,
  "recovery_percentage": 0.5,
  "long_short_balance_factor": 0.9,
  "max_long_short_ratio": 1.1
}
```

## Recovery Mode

When the portfolio drawdown exceeds the maximum allowed threshold, the system enters "recovery mode":

1. **Hard Recovery Mode**: Prohibits all new positions for a cooling-off period
2. **Soft Recovery Mode**: Allows trading with reduced position sizes
3. **Automatic Exit**: Requires automatic exit of positions upon hitting the maximum drawdown

The recovery mode is exited when:
- The portfolio value recovers to a specified percentage of the drawdown
- The cooling-off period (default: 10 days) has elapsed

## Implementation

The risk management system is implemented in the `RiskManager` class which:

1. Calculates and enforces position sizing limits
2. Monitors portfolio drawdown and triggers recovery mode when necessary
3. Enforces balanced exposure between long and short positions
4. Calculates component budgets based on premium collected
5. Validates trade balance before execution

The system integrates with the BacktestEngine by:

1. Limiting position sizes for both index and component options
2. Using premium collected from index options to determine component option budgets
3. Verifying that long and short exposures remain within acceptable ratios
4. Preventing imbalanced trades that could result in unexpected risks

## Future Improvements

Potential enhancements to the risk management system:

1. Dynamic adjustment of the balance factor based on market conditions
2. Integration of options Greeks (delta, gamma, vega, theta) into risk calculations
3. Weighted component allocation based on correlation analysis
4. Stress testing for extreme market scenarios
5. Advanced VaR (Value at Risk) calculations for better risk measurement