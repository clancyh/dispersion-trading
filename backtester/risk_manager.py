import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class RiskManager:
    """
    Risk management system to control portfolio risk and prevent excessive losses
    """
    
    def __init__(self, config):
        """
        Initialize the risk manager with configuration parameters
        
        Parameters:
        -----------
        config : dict
            Dictionary containing risk management configuration
        """
        self.config = config
        self.risk_config = config.get('risk_management', {})
        self.risk_enabled = self.risk_config.get('risk_limits_enabled', True)
        
        # Risk limits
        self.max_portfolio_risk_pct = self.risk_config.get('max_portfolio_risk_pct', 0.2)
        self.max_position_risk_pct = self.risk_config.get('max_position_risk_pct', 0.05)
        self.stop_loss_pct = self.risk_config.get('stop_loss_pct', 0.15)
        self.max_drawdown_pct = self.risk_config.get('max_drawdown_pct', 0.25)
        self.max_options_vega = self.risk_config.get('max_options_vega_exposure', 50000)
        self.max_options_theta = self.risk_config.get('max_options_theta_per_day', -5000)
        
        # Recovery parameters
        self.recovery_days = self.risk_config.get('recovery_days_after_max_drawdown', 10)
        self.recovery_pct = self.risk_config.get('recovery_percentage', 0.5)  # Requires 50% recovery from max drawdown
        
        # Trade balance parameters
        self.long_short_balance_factor = self.risk_config.get('long_short_balance_factor', 0.9)
        self.max_long_short_ratio = self.risk_config.get('max_long_short_ratio', 1.1)
        
        # Position sizing method
        self.position_sizing_method = self.risk_config.get('position_sizing_method', 'equal_risk')
        
        # Tracking variables
        self.current_portfolio_value = None
        self.peak_portfolio_value = None
        self.current_drawdown = 0
        self.positions = {}
        self.initial_portfolio_value = config['portfolio']['initial_cash']
        
        # Max drawdown tracking
        self.max_drawdown_hit = False
        self.max_drawdown_date = None
        self.recovery_target_value = None
        self.recovery_mode = False
        self.max_drawdown_date_value = None
        
        # Recovery mode flags and settings
        self.hard_recovery_mode = False  # Complete trading pause
        self.soft_recovery_mode = False  # Reduced position sizing
        self.recovery_scaling_factor = 0.5  # Position size reduction during soft recovery
        
        # Logger will be set later by the backtest engine
        self.logger = None
        
    def set_logger(self, logger):
        """Set the logger instance for this risk manager"""
        self.logger = logger
        
    def set_portfolio_value(self, value, current_date=None):
        """
        Update the current portfolio value and calculate drawdown
        
        Parameters:
        -----------
        value : float
            Current portfolio value
        current_date : datetime.date, optional
            Current date for tracking recovery periods
        
        Returns:
        --------
        bool
            True if portfolio is within risk limits, False otherwise
        """
        self.current_portfolio_value = value
        
        # Initialize peak value if not set
        if self.peak_portfolio_value is None:
            self.peak_portfolio_value = value
        else:
            self.peak_portfolio_value = max(self.peak_portfolio_value, value)
        
        # Calculate current drawdown
        if self.peak_portfolio_value > 0:
            self.current_drawdown = (self.peak_portfolio_value - value) / self.peak_portfolio_value
        else:
            self.current_drawdown = 0
        
        # If we're in recovery mode, check if we should exit or change modes
        if self.recovery_mode:
            days_in_recovery = (current_date - self.max_drawdown_date).days if current_date else 0
            recovery_progress = max(0, (value - self.max_drawdown_date_value)) / (self.recovery_target_value - self.max_drawdown_date_value)
            
            # Check for full recovery (returning to previous peak)
            if value >= self.peak_portfolio_value:
                if self.logger:
                    self.logger.info(f"Full recovery complete: Portfolio value (${value:,.2f}) exceeds previous peak (${self.peak_portfolio_value:,.2f}). Resuming normal trading.")
                # Exit all recovery modes
                self.recovery_mode = False
                self.hard_recovery_mode = False
                self.soft_recovery_mode = False
                self.current_drawdown = 0
                self.max_drawdown_hit = False
                return True
            
            # Check for transition from hard to soft recovery mode after cooling period
            elif self.hard_recovery_mode and days_in_recovery >= self.recovery_days:
                if self.logger:
                    self.logger.info(f"Transitioning to soft recovery mode after {days_in_recovery} days. Resuming trading with reduced risk.")
                self.hard_recovery_mode = False
                self.soft_recovery_mode = True
                return True
            
            # Still in recovery mode
            if days_in_recovery % 5 == 0 and self.logger:  # Only log every 5 days
                mode_status = "HARD" if self.hard_recovery_mode else "SOFT"
                self.logger.info(f"In {mode_status} recovery mode: Day {days_in_recovery}. Value: ${value:,.2f}, Peak: ${self.peak_portfolio_value:,.2f}, Progress: {recovery_progress:.2%}")
            
            # Return trading permission based on recovery mode
            return not self.hard_recovery_mode
        
        # Check if drawdown exceeds maximum allowed
        if self.risk_enabled and self.current_drawdown > self.max_drawdown_pct and not self.max_drawdown_hit:
            if self.logger:
                self.logger.warning(f"Maximum drawdown exceeded: {self.current_drawdown:.2%} > {self.max_drawdown_pct:.2%}")
            self.max_drawdown_hit = True
            
            if current_date is not None:
                # Enter hard recovery mode
                self.max_drawdown_date = current_date
                self.recovery_mode = True
                self.hard_recovery_mode = True
                self.soft_recovery_mode = False
                
                # Store the value at max drawdown for calculating progress
                self.max_drawdown_date_value = value
                
                # Calculate recovery target - we need to recover by recovery_pct of the drawdown amount
                drawdown_amount = self.peak_portfolio_value - value
                recovery_amount = drawdown_amount * self.recovery_pct
                self.recovery_target_value = value + recovery_amount
                
                if self.logger:
                    self.logger.warning(f"Entering hard recovery mode. Current value: ${value:,.2f}, Peak: ${self.peak_portfolio_value:,.2f}")
                    self.logger.info(f"Initial cooling period: {self.recovery_days} trading days")
                    self.logger.info(f"Full recovery target: ${self.peak_portfolio_value:,.2f}")
                
            return False
        
        # Reset drawdown hit flag if we're below the threshold
        if self.current_drawdown < self.max_drawdown_pct:
            self.max_drawdown_hit = False
            
        return True
    
    def should_close_all_positions(self):
        """
        Check if all positions should be closed due to excessive risk
        
        Returns:
        --------
        bool
            True if all positions should be closed, False otherwise
        """
        if not self.risk_enabled:
            return False
            
        # Check drawdown against limit - note we only force close when first hitting max drawdown
        if self.current_drawdown > self.max_drawdown_pct and not self.max_drawdown_hit:
            if self.logger:
                self.logger.warning(f"Closing all positions due to maximum drawdown: {self.current_drawdown:.2%}")
            return True
            
        # Check if portfolio value has dropped below a threshold
        if self.current_portfolio_value < 0.5 * self.initial_portfolio_value:
            if self.logger:
                self.logger.warning(f"Closing all positions due to significant portfolio value drop")
            return True
            
        return False
        
    def can_enter_new_trades(self, current_date=None):
        """
        Check if the system can enter new trades based on risk state
        
        Parameters:
        -----------
        current_date : datetime.date, optional
            Current date for tracking recovery periods
            
        Returns:
        --------
        bool
            True if new trades are allowed, False otherwise
        """
        # Don't enter trades during hard recovery mode
        if self.hard_recovery_mode:
            days_in_recovery = 0
            if current_date is not None and self.max_drawdown_date is not None:
                days_in_recovery = (current_date - self.max_drawdown_date).days
                
            if self.logger:
                self.logger.info(f"In hard recovery mode (Day {days_in_recovery}/{self.recovery_days}). Not entering new trades.")
            return False
            
        # Allow trades during soft recovery mode (risk adjustment happens in position sizing)
        if self.soft_recovery_mode:
            # We can enter trades, but with reduced size - handled by calculate_position_sizing
            return True
            
        # Don't enter trades if we're over the max drawdown limit
        if self.current_drawdown > self.max_drawdown_pct:
            return False
            
        return True
    
    def check_position_stop_loss(self, position):
        """
        Check if a position has hit its stop-loss level
        
        Parameters:
        -----------
        position : dict
            Position data dictionary
        
        Returns:
        --------
        bool
            True if stop-loss has been triggered, False otherwise
        """
        if not self.risk_enabled:
            return False
            
        # Calculate position P&L
        entry_value = position.get('entry_value', 0)
        current_value = position.get('current_value', 0)
        
        # For short positions, entry value will be negative
        if entry_value < 0:
            profit_loss_pct = (entry_value - current_value) / abs(entry_value)
        else:
            profit_loss_pct = (current_value - entry_value) / abs(entry_value)
        
        # Check if loss exceeds stop-loss percentage
        if profit_loss_pct < -self.stop_loss_pct:
            if self.logger:
                self.logger.warning(f"Stop-loss triggered for {position['ticker']} {position['option_type']} option: {profit_loss_pct:.2%}")
            return True
            
        return False
    
    def calculate_position_sizing(self, strategy_type, ticker, option_type, option_price, portfolio_value):
        """
        Calculate appropriate position sizing based on risk parameters
        
        Parameters:
        -----------
        strategy_type : str
            Type of strategy ('dispersion' or 'reverse_dispersion')
        ticker : str
            Ticker symbol
        option_type : str
            Option type ('call' or 'put')
        option_price : float
            Current option price
        portfolio_value : float
            Current portfolio value
            
        Returns:
        --------
        int
            Number of option contracts to trade
        """
        if not self.risk_enabled:
            # Default to 5% of portfolio if risk management is disabled
            return int(0.05 * portfolio_value / (option_price * 100))
        
        # In hard recovery mode, don't enter new positions
        # But allow reduced position sizing in soft recovery mode
        if self.recovery_mode and self.hard_recovery_mode:
            return 0
        
        # Calculate maximum risk amount for this position
        max_position_risk = portfolio_value * self.max_position_risk_pct
        
        # Calculate maximum number of contracts based on risk
        if self.position_sizing_method == 'equal_risk':
            # Risk the same dollar amount on each position
            # For options, we use the option price as an approximation of max risk
            contracts = int(max_position_risk / (option_price * 100))
        elif self.position_sizing_method == 'kelly':
            # A simplified Kelly criterion approach
            # For dispersion trades, we're using a more conservative approach
            contracts = int(0.5 * max_position_risk / (option_price * 100))
        else:
            # Default to percentage of portfolio value
            contracts = int(self.max_position_risk_pct * portfolio_value / (option_price * 100))
        
        # Always ensure at least 1 contract (if any)
        if contracts == 0 and option_price > 0:
            contracts = 1
        
        # Apply scaling factor during soft recovery mode
        if self.soft_recovery_mode:
            contracts = int(contracts * self.recovery_scaling_factor)
            if self.logger:
                self.logger.info(f"Soft recovery mode: Reducing position size by {(1-self.recovery_scaling_factor)*100:.0f}%")
        
        return contracts
    
    def check_portfolio_risk(self, new_position_value, portfolio_value):
        """
        Check if adding a new position would exceed portfolio risk limits
        
        Parameters:
        -----------
        new_position_value : float
            Value of the new position
        portfolio_value : float
            Current portfolio value
            
        Returns:
        --------
        bool
            True if within risk limits, False otherwise
        """
        if not self.risk_enabled:
            return True
            
        # Only block new positions in hard recovery mode
        if self.hard_recovery_mode:
            return False
            
        # Calculate total risk with new position
        total_risk = abs(new_position_value) / portfolio_value
        
        # Check if total risk exceeds maximum allowed
        if total_risk > self.max_portfolio_risk_pct:
            if self.logger:
                self.logger.warning(f"WARNING: Adding position would exceed portfolio risk limit: {total_risk:.2%} > {self.max_portfolio_risk_pct:.2%}")
            return False
            
        return True
    
    def update_positions(self, positions):
        """
        Update the positions tracked by the risk manager
        
        Parameters:
        -----------
        positions : dict
            Dictionary of current positions
        """
        self.positions = positions
    
    def check_greeks_exposure(self, new_position_greeks):
        """
        Check if adding a new position would exceed options Greeks exposure limits
        
        Parameters:
        -----------
        new_position_greeks : dict
            Greeks values for the new position
            
        Returns:
        --------
        bool
            True if within exposure limits, False otherwise
        """
        if not self.risk_enabled:
            return True
            
        # Only block new positions in hard recovery mode
        if self.hard_recovery_mode:
            return False
            
        # For simplicity in the current implementation, we're not calculating actual Greeks
        # This would be expanded in a production system with proper options Greeks calculations
        return True
    
    def get_status_dict(self):
        """
        Get a dictionary with the current risk management status
        
        Returns:
        --------
        dict
            Dictionary with risk management status information
        """
        return {
            'risk_enabled': self.risk_enabled,
            'current_drawdown': self.current_drawdown,
            'max_drawdown_limit': self.max_drawdown_pct,
            'peak_portfolio_value': self.peak_portfolio_value,
            'current_portfolio_value': self.current_portfolio_value,
            'recovery_mode': self.recovery_mode,
            'recovery_target_value': self.recovery_target_value,
            'max_drawdown_date': self.max_drawdown_date,
            'recovery_days': self.recovery_days,
            'recovery_pct': self.recovery_pct,
            'max_drawdown_date_value': self.max_drawdown_date_value
        }
    
    def calculate_balanced_component_budget(self, premium_collected, portfolio_value):
        """
        Calculate a balanced budget for component options based on the premium collected
        from index options
        
        Parameters:
        -----------
        premium_collected : float
            Premium collected from short index options
        portfolio_value : float
            Current portfolio value
            
        Returns:
        --------
        float
            Budget for component options purchases
        """
        if not self.risk_enabled:
            # Default to a fixed percentage if risk management is disabled
            return portfolio_value * 0.2
        
        # In recovery mode, don't enter new positions
        if self.recovery_mode:
            return 0
        
        # Base component budget on premium collected, with a balance factor
        # The balance factor should be slightly less than 1.0 to ensure a net credit
        component_budget = premium_collected * self.long_short_balance_factor
        
        # Add a safety check for max percentage of portfolio
        max_budget = portfolio_value * self.max_portfolio_risk_pct
        if component_budget > max_budget:
            if self.logger:
                self.logger.info(f"Limiting component budget to {self.max_portfolio_risk_pct:.2%} of portfolio")
            component_budget = max_budget
            
        return component_budget
        
    def check_trade_balance(self, long_exposure, short_exposure):
        """
        Check if the trade has a balanced exposure between long and short sides
        
        Parameters:
        -----------
        long_exposure : float
            Total long exposure in dollars
        short_exposure : float
            Total short exposure in dollars (should be negative)
            
        Returns:
        --------
        bool
            True if the trade is balanced, False otherwise
        """
        if not self.risk_enabled:
            return True
            
        # Don't check balance in recovery mode
        if self.recovery_mode:
            return False
            
        # Ensure short_exposure is negative to compare magnitudes properly
        short_exposure = abs(short_exposure)
        
        # Ensure we have some exposure on both sides
        if long_exposure <= 0 or short_exposure <= 0:
            if self.logger:
                self.logger.warning("Trade is not balanced: Missing exposure on one side")
            return False
            
        # Calculate the ratio
        long_short_ratio = long_exposure / short_exposure if short_exposure > 0 else float('inf')
        
        # Check if the ratio is within acceptable limits
        if long_short_ratio > self.max_long_short_ratio:
            if self.logger:
                self.logger.warning(f"Trade is not balanced: Long/short ratio {long_short_ratio:.2f} exceeds limit {self.max_long_short_ratio:.2f}")
            return False
            
        return True 