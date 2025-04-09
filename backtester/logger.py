import datetime
from typing import Dict, Any, Optional


class BacktestLogger:
    """
    Centralized logging utility for the backtesting engine.
    Controls output verbosity based on config settings.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the logger with configuration settings"""
        self.config = config
        self.log_config = config.get('logging', {})
        self.debug_mode = self.log_config.get('debug_mode', False)
        self.log_level = self.log_config.get('level', 'info').lower()
        self.console_config = self.log_config.get('console_output', {})
        
        # Configure what to show
        self.show_signals = self.console_config.get('show_signals', True)
        self.show_trades = self.console_config.get('show_trades', True)
        self.performance_update_frequency = self.console_config.get('performance_update_frequency', 5)
        self.verbose_portfolio_updates = self.console_config.get('verbose_portfolio_updates', False)
        
        # Track days since last performance update
        self.days_since_performance_update = 0
        self.current_date = None
        
    def debug(self, message: str) -> None:
        """Log debug message (only in debug mode)"""
        if self.debug_mode:
            self._log("DEBUG", message)
    
    def info(self, message: str) -> None:
        """Log info message (always shown unless level is warning or error)"""
        if self.log_level in ['info', 'debug']:
            self._log("INFO", message)
    
    def warning(self, message: str) -> None:
        """Log warning message (always shown unless level is error)"""
        if self.log_level in ['info', 'debug', 'warning']:
            self._log("WARNING", message)
    
    def error(self, message: str) -> None:
        """Log error message (always shown)"""
        self._log("ERROR", message)
    
    def _log(self, level: str, message: str) -> None:
        """Internal logging function"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def update_date(self, current_date) -> None:
        """Update the current date and track days since performance update"""
        self.current_date = current_date
        self.days_since_performance_update += 1
    
    # Signal logging
    def log_signal(self, signal_type: str, metrics: Optional[Dict[str, Any]] = None) -> None:
        """Log trading signal based on configuration"""
        if not self.show_signals:
            return
            
        if metrics:
            if signal_type == "ENTER_DISPERSION":
                self.info(f"SIGNAL: Enter dispersion trade. DSPX Z-Score: {metrics.get('z_score', 'N/A'):.2f}")
            elif signal_type == "ENTER_REVERSE_DISPERSION":
                self.info(f"SIGNAL: Enter reverse dispersion trade. DSPX Z-Score: {metrics.get('z_score', 'N/A'):.2f}")
            elif signal_type == "EXIT":
                self.info(f"SIGNAL: Exit dispersion positions. DSPX Z-Score: {metrics.get('z_score', 'N/A'):.2f}")
            else:
                self.info(f"SIGNAL: {signal_type}")
        else:
            self.info(f"SIGNAL: {signal_type}")
    
    # Trade logging
    def log_trade(self, ticker: str, trade_type: str, position_type: str, 
                  quantity: float, price: float, value: float, 
                  option_details: Optional[Dict[str, Any]] = None) -> None:
        """Log trade execution based on configuration"""
        if not self.show_trades:
            return
            
        if option_details:
            option_str = f"{option_details.get('option_type', '')} option, strike: ${option_details.get('strike_price', 0):.2f}, expiry: {option_details.get('expiration_date', '')}"
            self.info(f"TRADE: {trade_type} {position_type} {abs(quantity)} {ticker} {option_str} @ ${price:.2f}, value: ${abs(value):.2f}")
        else:
            self.info(f"TRADE: {trade_type} {position_type} {abs(quantity)} {ticker} @ ${price:.2f}, value: ${abs(value):.2f}")
    
    # Performance update logging
    def log_portfolio_update(self, portfolio_value: float, cash: float, 
                            long_exposure: float, short_exposure: float,
                            drawdown: float) -> None:
        """Log portfolio performance update based on configuration and frequency"""
        # Always output if verbose or it's time for an update
        if self.verbose_portfolio_updates or self.days_since_performance_update >= self.performance_update_frequency:
            self.info(f"PORTFOLIO: Value: ${portfolio_value:,.2f}, Cash: ${cash:,.2f}, " +
                      f"Net Exposure: ${long_exposure + short_exposure:,.2f}, Drawdown: {drawdown:.2%}")
            self.days_since_performance_update = 0
            
            # Extra details in verbose mode
            if self.verbose_portfolio_updates:
                self.debug(f"PORTFOLIO DETAIL: Long Exposure: ${long_exposure:,.2f}, " + 
                           f"Short Exposure: ${short_exposure:,.2f}")
    
    # Risk management logging
    def log_risk_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log risk management status updates"""
        self.warning(f"RISK: {status}")
        if details and self.debug_mode:
            for key, value in details.items():
                if isinstance(value, float):
                    self.debug(f"RISK DETAIL: {key}: {value:.2f}")
                else:
                    self.debug(f"RISK DETAIL: {key}: {value}")
    
    # Strategy-specific logging
    def log_dispersion_trade_status(self, exposure_info: Dict[str, float], balanced: bool) -> None:
        """Log dispersion trade execution status"""
        if self.debug_mode:
            # Detailed exposure info in debug mode
            for key, value in exposure_info.items():
                self.debug(f"DISPERSION: {key}: ${value:,.2f}")
        else:
            # Simplified output in normal mode
            self.info(f"DISPERSION: Long: ${exposure_info.get('long_exposure', 0):,.2f}, " +
                      f"Short: ${exposure_info.get('short_exposure', 0):,.2f}, " +
                      f"Premium: ${exposure_info.get('premium', 0):,.2f}")
        
        if not balanced:
            self.warning("DISPERSION: Trade exposure is not balanced") 