import pandas as pd
import os
from datetime import datetime, timedelta
from backtester.correlation import calculate_correlation_dispersion
from backtester.options_pricer import price_options
from backtester.dspx import load_dspx_data, calculate_dspx_signal
from backtester.risk_manager import RiskManager
from backtester.logger import BacktestLogger
import numpy as np
from .weights import load_index_weights

class BacktestEngine:
    def __init__(self, config):
        # Load configuration
        self.config = config
        self.start_date = config['backtest']['start_date']
        self.end_date = config['backtest']['end_date']
        self.initial_cash = config['portfolio']['initial_cash']
        
        # Initialize logger
        self.logger = BacktestLogger(config)
        
        # Portfolio state
        self.current_date = None
        self.current_cash = self.initial_cash
        self.positions = {}  # Will hold all option and stock positions
        
        # Performance tracking
        self.portfolio_history = []  # Daily portfolio values
        self.trade_history = []      # Record of all trades
        
        # Initialize risk manager
        self.risk_manager = RiskManager(config)
        self.risk_manager.set_logger(self.logger)
        
        # Initialize data
        self._load_data()
        
    def _load_data(self):
        """Load and prepare data for the backtest"""
        # Import data loading utilities
        import os
        import pandas as pd
        from datetime import datetime
        import numpy as np
        
        # Set up trading dates range
        start_date = datetime.strptime(self.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(self.end_date, '%Y-%m-%d').date()
        
        # Load stock price data
        self.price_data = {}
        self.index_ticker = self.config['universe']['index']
        
        # Load index data
        index_file = f"{self.config['paths']['data_dir']}{self.index_ticker}.csv"
        if not os.path.exists(index_file):
            raise FileNotFoundError(f"Index data file not found: {index_file}")
        
        index_data = pd.read_csv(index_file)
        index_data['date'] = pd.to_datetime(index_data['date'])
        
        # Filter for the backtest period
        index_data = index_data[(index_data['date'].dt.date >= start_date) & 
                               (index_data['date'].dt.date <= end_date)]
        
        self.price_data[self.index_ticker] = index_data
        
        # Load VIX data for volatility calculations
        vix_file = f"{self.config['paths']['data_dir']}^VIX.csv"
        if os.path.exists(vix_file):
            vix_data = pd.read_csv(vix_file)
            vix_data['date'] = pd.to_datetime(vix_data['date'])
            
            # Remove rows with NA values in critical columns
            vix_data = vix_data.dropna(subset=['Close', 'Adjusted'])
            
            # Only keep dates that exist in the index data to ensure alignment
            vix_data = vix_data[vix_data['date'].dt.date.isin(index_data['date'].dt.date)]
            
            self.price_data['^VIX'] = vix_data
        else:
            self.logger.warning("VIX data not found. Implied volatility calculations will use historical volatility.")
        
        # Set up component universe
        if self.config['universe']['random_selection']:
            # Load S&P500 constituents
            constituents_file = "constituents-sp500.csv"
            if not os.path.exists(constituents_file):
                raise FileNotFoundError(f"Constituents file not found: {constituents_file}")
            
            constituents = pd.read_csv(constituents_file)
            
            # Set random seed for reproducibility
            np.random.seed(self.config['universe']['seed'])
            
            # Randomly select stocks
            num_stocks = min(self.config['universe']['num_stocks'], len(constituents))
            selected_tickers = np.random.choice(
                constituents['Symbol'], 
                size=num_stocks, 
                replace=False
            )
            
            self.component_tickers = list(selected_tickers)
        else:
            # Use predefined list
            self.component_tickers = self.config.get('universe', {}).get('tickers', [])
        
        # Load component data
        valid_components = []
        valid_trading_dates = set(index_data['date'].dt.date)
        
        for ticker in self.component_tickers:
            stock_file = f"{self.config['paths']['data_dir']}{ticker}.csv"
            if not os.path.exists(stock_file):
                self.logger.warning(f"Data for {ticker} not found, excluding from universe.")
                continue
            
            stock_data = pd.read_csv(stock_file)
            stock_data['date'] = pd.to_datetime(stock_data['date'])
            
            # Filter for the backtest period
            stock_data = stock_data[(stock_data['date'].dt.date >= start_date) & 
                                   (stock_data['date'].dt.date <= end_date)]
            
            # Remove any rows with NA values in price columns
            stock_data = stock_data.dropna(subset=['Close', 'Adjusted'])
            
            # Ensure stock has data for all trading dates
            stock_dates = set(stock_data['date'].dt.date)
            if len(stock_dates.intersection(valid_trading_dates)) < len(valid_trading_dates) * 0.9:
                self.logger.warning(f"{ticker} has insufficient data coverage, excluding from universe.")
                continue
            
            self.price_data[ticker] = stock_data
            valid_components.append(ticker)
        
        # Update component tickers to only include valid ones
        self.component_tickers = valid_components
        self.logger.info(f"Using {len(self.component_tickers)} components for dispersion trading.")
        
        # Ensure all data sources have the same trading days
        # Get intersection of all available dates
        common_dates = set(index_data['date'].dt.date)
        for ticker, df in self.price_data.items():
            common_dates = common_dates.intersection(set(df['date'].dt.date))
        
        # Filter all data to only include common dates
        for ticker in self.price_data:
            self.price_data[ticker] = self.price_data[ticker][
                self.price_data[ticker]['date'].dt.date.isin(common_dates)
            ]
        
        # Extract trading dates from index data
        self.trading_dates = sorted(list(common_dates))
        
        # Load DSPX data if available
        try:
            self.dspx_data = load_dspx_data(logger=self.logger)
            # Ensure DSPX data only includes available trading dates
            self.dspx_data = self.dspx_data[self.dspx_data['date'].dt.date.isin(common_dates)]
            self.logger.info(f"Loaded DSPX data with {len(self.dspx_data)} entries.")
        except Exception as e:
            self.logger.warning(f"Could not load DSPX data: {e}")
            self.dspx_data = None
        
    def _build_date_range(self):
        """Build a calendar of trading dates from the price data"""
        import pandas as pd
        
        # Create a set of all dates from all price data
        all_dates = set()
        for ticker, data in self.price_data.items():
            all_dates.update(data['date'].dt.date)
        
        # Convert to sorted list
        self.trading_dates = sorted(list(all_dates))
        
        # Filter to backtest date range
        start = pd.to_datetime(self.start_date).date()
        end = pd.to_datetime(self.end_date).date()
        self.trading_dates = [d for d in self.trading_dates if start <= d <= end]
    
    def run(self):
        """Run the backtest"""
        self.logger.info(f"Starting backtest from {self.start_date} to {self.end_date}")
        self.logger.info(f"Trading universe: {self.index_ticker} and {len(self.component_tickers)} components")
        
        # Initialize portfolio
        self.current_cash = self.initial_cash
        self.positions = {}
        self.portfolio_history = []
        self.trade_history = []
        
        # Iterate through each trading day
        for date in self.trading_dates:
            self.current_date = date
            self.logger.update_date(date)
            self._process_trading_day()
            
        # Calculate final performance metrics
        self._calculate_performance()
        
        return self._get_results()
    
    def _process_trading_day(self):
        """Process a single trading day in the backtest"""
        # 1. Update values of existing positions
        self._update_position_values()
        
        # 2. Check for expired options and close those positions
        self._process_expirations()
        
        # 3. Generate trading signals if we're not in a high-risk state
        signals = None
        if not self.risk_manager.should_close_all_positions():
            # Only generate signals if we can enter new trades
            if self.risk_manager.can_enter_new_trades(self.current_date):
                signals = self._generate_signals(self.current_date)
            else:
                self.logger.debug(f"Not generating signals on {self.current_date} due to risk management constraints")
        
        # 4. Execute trades based on signals
        if signals:
            self._execute_trades(signals, self.current_date)
        
        # 5. Record end-of-day portfolio value
        self._record_portfolio_value()
    
    def _update_position_values(self):
        """Update the value of all open positions"""
        # For each position, calculate its current market value
        portfolio_value = self.current_cash
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            # If the position is still open
            if position['status'] == 'open':
                current_value = self._calculate_position_value(position)
                position['current_value'] = current_value
                portfolio_value += current_value
                
                # Check if stop-loss has been triggered
                if self.risk_manager.check_position_stop_loss(position):
                    positions_to_close.append(position_id)
        
        # Close positions that hit stop-loss
        for position_id in positions_to_close:
            self._close_position(position_id, self.positions[position_id], reason="stop_loss")
            
        # Update portfolio value
        self.current_portfolio_value = portfolio_value
        
        # Update risk manager with new portfolio value and positions
        self.risk_manager.set_portfolio_value(portfolio_value, self.current_date)
        self.risk_manager.update_positions(self.positions)
        
        # Check if we should close all positions due to excessive risk
        if self.risk_manager.should_close_all_positions():
            self._close_all_positions(reason="risk_limit")
    
    def _calculate_position_value(self, position):
        """Calculate the current value of a position"""
        from backtester.options_pricer import price_options
        
        position_type = position['type']
        ticker = position['ticker']
        quantity = position['quantity']
        
        if position_type == 'stock':
            # For stocks, just get the current price
            current_price = self._get_price_on_date(ticker, self.current_date)
            return quantity * current_price
        
        elif position_type == 'option':
            # For options, we need to price them based on current parameters
            current_date = self.current_date
            expiration_date = position['expiration_date']
            strike_price = position['strike_price']
            option_type = position['option_type']
            
            # Calculate option price using our pricing model
            try:
                option_price = self._price_option(
                    ticker=ticker,
                    current_date=current_date,
                    expiration_date=expiration_date,
                    strike_price=strike_price,
                    option_type=option_type
                )
                
                return quantity * option_price * 100  # Standard options contracts are for 100 shares
            
            except Exception as e:
                self.logger.error(f"Error pricing option {position_id}: {e}")
                return position['current_value']  # Return previous value if error
    
    def _get_price_on_date(self, ticker, date):
        """Get the price of a ticker on a specific date"""
        if ticker not in self.price_data:
            raise ValueError(f"No price data available for {ticker}")
        
        # Find the price on the given date or the most recent price before it
        price_data = self.price_data[ticker]
        matching_prices = price_data[price_data['date'].dt.date <= date]
        
        if matching_prices.empty:
            raise ValueError(f"No price data available for {ticker} on or before {date}")
        
        return matching_prices.iloc[-1]['Adjusted']
    
    def _process_expirations(self):
        """Check for and process expired options"""
        for position_id, position in self.positions.items():
            if position['type'] == 'option' and position['status'] == 'open':
                expiration_date = position['expiration_date']
                
                # Check if the option has expired
                if expiration_date <= self.current_date:
                    # Calculate the expiration value (intrinsic value at expiration)
                    self._close_expired_option(position_id, position)
    
    def _close_expired_option(self, position_id, position):
        """Close an expired option position"""
        ticker = position['ticker']
        strike = position['strike_price']
        option_type = position['option_type']
        quantity = position['quantity']
        
        # Get underlying price at expiration
        underlying_price = self._get_price_on_date(ticker, self.current_date)
        
        # Calculate intrinsic value at expiration
        if option_type == 'call':
            intrinsic_value = max(0, underlying_price - strike)
        else:  # put
            intrinsic_value = max(0, strike - underlying_price)
        
        # Update portfolio cash with the option's value at expiration
        position_value = intrinsic_value * quantity * 100  # 100 shares per contract
        self.current_cash += position_value
        
        # Mark position as closed
        position['status'] = 'closed'
        position['exit_date'] = self.current_date
        position['exit_price'] = intrinsic_value
        position['exit_value'] = position_value
        
        # Record the trade
        self._record_trade(
            ticker=ticker,
            trade_type='close',
            position_type='option',
            quantity=quantity,
            price=intrinsic_value,
            value=position_value,
            option_details={
                'strike': strike,
                'expiration': position['expiration_date'],
                'option_type': option_type
            }
        )
    
    def _generate_signals(self, current_date):
        """Generate trading signals for the current date"""
        signals = {'signal': None, 'metrics': {}}
        
        try:
            # Check if we already have dispersion positions open
            has_open_positions = self._has_open_dispersion_positions()
            
            # If DSPX data is available, use it for signals
            if self.dspx_data is not None:
                signal_data = calculate_dspx_signal(
                    self.dspx_data, 
                    current_date,
                    self.config['dispersion']['entry_threshold'],
                    self.config['dispersion']['exit_threshold'],
                    self.config['dispersion']['dspx_lookback']
                )
                
                signals['signal'] = signal_data['signal']
                signals['metrics'] = signal_data['metrics']
                
                # Log the signal
                self.logger.log_signal(signals['signal'], signals['metrics'])
                
            else:
                # If no DSPX data, use correlation dispersion to generate signals
                # Implement this if DSPX data is not available
                self.logger.warning("No DSPX data available. Using basic correlation signal.")
                
                # Simple implementation of correlation-based signal
                # This is a placeholder and should be enhanced
                dispersion = calculate_correlation_dispersion(
                    self.price_data, 
                    self.component_tickers, 
                    self.index_ticker, 
                    current_date, 
                    30  # lookback period
                )
                
                # Convert dispersion to signal
                if dispersion > 0.2 and not has_open_positions:
                    signals['signal'] = 'ENTER_DISPERSION'
                elif dispersion < 0.1 and has_open_positions:
                    signals['signal'] = 'EXIT'
                else:
                    signals['signal'] = 'HOLD'
                
                signals['metrics'] = {'dispersion': dispersion}
                
                # Log the signal
                self.logger.log_signal(signals['signal'], signals['metrics'])
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals on {current_date}: {e}")
            return {'signal': 'HOLD', 'metrics': {}}
    
    def _has_open_dispersion_positions(self):
        """Check if there are open dispersion positions"""
        for position in self.positions.values():
            if position['status'] == 'open' and position['strategy'] == 'dispersion':
                return True
        return False
    
    def _execute_trades(self, signals, current_date):
        """Execute trades based on signals and risk management constraints"""
        # Only execute trades if risk manager allows it
        if not self.risk_manager.can_enter_new_trades(current_date):
            if self.risk_manager.hard_recovery_mode:
                self.logger.info("In hard recovery mode - not executing any new trades.")
            elif self.risk_manager.soft_recovery_mode:
                self.logger.info("In soft recovery mode - executing trades at reduced size.")
                # Continue with execution
            else:
                self.logger.info("Risk constraints prevent entering new trades.")
            return
        
        # Implementation will vary based on your specific strategy requirements
        if signals['signal'] == 'ENTER_DISPERSION':
            self._enter_dispersion_trade()
        elif signals['signal'] == 'ENTER_REVERSE_DISPERSION':
            self._enter_reverse_dispersion_trade()
        elif signals['signal'] == 'EXIT':
            self._exit_dispersion_trades()
    
    def _enter_dispersion_trade(self):
        """
        Execute a dispersion trade:
        - Short index options (collect premium)
        - Long component options (pay premium)
        
        This is used when implied correlation is higher than realized correlation.
        """
        from datetime import timedelta
        from .weights import load_index_weights
        
        # 1. Calculate the option parameters - use at least 30 calendar days (about 1 month)
        target_expiry = self.current_date + timedelta(days=30)
        
        # Find the nearest valid trading day to our target expiry
        valid_expiry_days = [d for d in self.trading_dates if d > self.current_date]
        if not valid_expiry_days:
            self.logger.warning(f"No valid expiry dates available after {self.current_date}")
            return
            
        # Use an expiry date that's at least 7 days in the future
        future_dates = [d for d in valid_expiry_days if (d - self.current_date).days >= 7]
        if not future_dates:
            self.logger.warning(f"No valid expiry dates at least 7 days after {self.current_date}")
            return
            
        # Choose the closest date to our target that's at least 7 days out
        min_expiry = future_dates[0]
        expiration_date = min([d for d in future_dates if (d - target_expiry).days >= 0] or [future_dates[-1]])
        
        # Log the expiration we're using
        days_to_expiry = (expiration_date - self.current_date).days
        self.logger.info(f"Setting up dispersion trade with {days_to_expiry} days to expiration (from {self.current_date} to {expiration_date})")
        
        # Track exposures
        total_short_exposure = 0
        
        # 2. Short the index option (ATM straddle - both call and put)
        index_price = self._get_price_on_date(self.index_ticker, self.current_date)
        index_strike = round(index_price)
        
        # Price the index options
        try:
            # Price index call
            index_call_price = self._price_option(
                ticker=self.index_ticker,
                current_date=self.current_date,
                expiration_date=expiration_date,
                strike_price=index_strike,
                option_type='call'
            )
            
            # Price index put
            index_put_price = self._price_option(
                ticker=self.index_ticker,
                current_date=self.current_date,
                expiration_date=expiration_date,
                strike_price=index_strike,
                option_type='put'
            )
            
            # Use risk manager to calculate position sizing
            index_call_contracts = self.risk_manager.calculate_position_sizing(
                'dispersion', 
                self.index_ticker, 
                'call', 
                index_call_price, 
                self.current_portfolio_value
            )
            
            index_put_contracts = self.risk_manager.calculate_position_sizing(
                'dispersion', 
                self.index_ticker, 
                'put', 
                index_put_price, 
                self.current_portfolio_value
            )
            
            # Check if positions would exceed portfolio risk limits
            call_value = -index_call_contracts * index_call_price * 100  # Negative for short
            put_value = -index_put_contracts * index_put_price * 100     # Negative for short
            
            if not self.risk_manager.check_portfolio_risk(call_value + put_value, self.current_portfolio_value):
                self.logger.info("Skipping trade due to portfolio risk limits")
                return
            
            # Execute the index trades (short)
            if index_call_contracts > 0:
                self._open_option_position(
                    ticker=self.index_ticker,
                    quantity=-index_call_contracts,  # Negative for short
                    strike_price=index_strike,
                    expiration_date=expiration_date,
                    option_type='call',
                    price=index_call_price,
                    strategy='dispersion'
                )
                total_short_exposure += call_value
            
            if index_put_contracts > 0:
                self._open_option_position(
                    ticker=self.index_ticker,
                    quantity=-index_put_contracts,  # Negative for short
                    strike_price=index_strike,
                    expiration_date=expiration_date,
                    option_type='put',
                    price=index_put_price,
                    strategy='dispersion'
                )
                total_short_exposure += put_value
            
            # Calculate the premium collected
            premium_collected = (index_call_price * index_call_contracts + 
                               index_put_price * index_put_contracts) * 100
            
            # Add the premium collected to our cash
            self.current_cash += premium_collected
            
            # Log the amount collected from shorting index options
            self.logger.info(f"Premium collected from index options: ${premium_collected:,.2f}")
            self.logger.info(f"Total short exposure: ${total_short_exposure:,.2f}")
            
            # If no premium was collected, exit
            if premium_collected <= 0:
                self.logger.info("No premium collected. Skipping component trades.")
                return
            
            # Use the risk manager to calculate a balanced component budget based on the premium collected
            component_premium_target = premium_collected * self.risk_manager.long_short_balance_factor
            
        except Exception as e:
            self.logger.error(f"Error pricing index options: {e}")
            return
        
        # 3. Long the component options (ATM straddles)
        if len(self.component_tickers) > 0:
            # Track the total premium spent and exposure
            total_premium_spent = 0
            total_long_exposure = 0
            
            # Load component weights from S&P 500 constituents file
            try:
                component_weights = load_index_weights(self.index_ticker)
                self.logger.info(f"Loaded weights for {len(component_weights)} constituents")
                
                # Filter to only include components in our universe
                valid_components = [ticker for ticker in self.component_tickers if ticker in component_weights]
                
                if len(valid_components) < 20:
                    self.logger.warning(f"Warning: Only {len(valid_components)} components with weights. Using top components.")
                    # Sort the component tickers by weight (descending)
                    sorted_components = sorted(
                        component_weights.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    # Take the top 50 components by weight
                    top_components = [comp[0] for comp in sorted_components[:50] 
                                     if comp[0] in self.component_tickers]
                    
                    if len(top_components) > 0:
                        valid_components = top_components
                    else:
                        # Fall back to equal weighting if no components match
                        valid_components = self.component_tickers[:50]
                        component_weights = {ticker: 1.0/len(valid_components) for ticker in valid_components}
                else:
                    # Take top 50 components by weight to focus exposure
                    filtered_weights = {ticker: component_weights[ticker] for ticker in valid_components}
                    sorted_components = sorted(
                        filtered_weights.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    valid_components = [comp[0] for comp in sorted_components[:50]]
                
                # Renormalize weights for selected components
                total_weight = sum(component_weights[ticker] for ticker in valid_components)
                normalized_weights = {
                    ticker: component_weights[ticker] / total_weight for ticker in valid_components
                }
                
                self.logger.info(f"Trading with {len(valid_components)} weighted components")
                
            except Exception as e:
                self.logger.error(f"Error loading component weights: {e}. Using equal weighting.")
                valid_components = self.component_tickers[:50]  # Limit to 50 components
                normalized_weights = {ticker: 1.0/len(valid_components) for ticker in valid_components}
            
            # Allocate the premium target across components based on their weights
            premium_target_per_component = {
                ticker: component_premium_target * normalized_weights[ticker]
                for ticker in valid_components
            }
            
            # Log the weighted allocation
            self.logger.info(f"Total target premium to spend: ${component_premium_target:,.2f}")
            
            for ticker in valid_components:
                try:
                    comp_price = self._get_price_on_date(ticker, self.current_date)
                    comp_strike = round(comp_price)
                    
                    target_premium = premium_target_per_component[ticker]
                    self.logger.info(f"Target premium for {ticker} (weight {normalized_weights[ticker]:.2%}): ${target_premium:,.2f}")
                    
                    # Price component call
                    comp_call_price = self._price_option(
                        ticker=ticker,
                        current_date=self.current_date,
                        expiration_date=expiration_date,
                        strike_price=comp_strike,
                        option_type='call'
                    )
                    
                    # Price component put
                    comp_put_price = self._price_option(
                        ticker=ticker,
                        current_date=self.current_date,
                        expiration_date=expiration_date,
                        strike_price=comp_strike,
                        option_type='put'
                    )
                    
                    # Calculate contracts needed to reach premium target (split between call and put)
                    target_call_contracts = int(target_premium / 2 / (comp_call_price * 100))
                    target_put_contracts = int(target_premium / 2 / (comp_put_price * 100))
                    
                    # Ensure minimum of 1 contract if target is positive
                    if target_call_contracts == 0 and target_premium > 0:
                        target_call_contracts = 1
                    if target_put_contracts == 0 and target_premium > 0:
                        target_put_contracts = 1
                    
                    # Limit by risk manager
                    risk_call_contracts = self.risk_manager.calculate_position_sizing(
                        'dispersion', 
                        ticker, 
                        'call', 
                        comp_call_price, 
                        self.current_portfolio_value * normalized_weights[ticker]
                    )
                    
                    risk_put_contracts = self.risk_manager.calculate_position_sizing(
                        'dispersion', 
                        ticker, 
                        'put', 
                        comp_put_price, 
                        self.current_portfolio_value * normalized_weights[ticker]
                    )
                    
                    # Use the minimum of target and risk-based sizing
                    comp_call_contracts = min(target_call_contracts, risk_call_contracts)
                    comp_put_contracts = min(target_put_contracts, risk_put_contracts)
                    
                    # Check if positions would exceed portfolio risk limits
                    call_value = comp_call_contracts * comp_call_price * 100
                    put_value = comp_put_contracts * comp_put_price * 100
                    
                    if not self.risk_manager.check_portfolio_risk(call_value + put_value, self.current_portfolio_value):
                        self.logger.info(f"Skipping {ticker} component trade due to portfolio risk limits")
                        continue
                    
                    # Execute the component trades (long)
                    if comp_call_contracts > 0:
                        self._open_option_position(
                            ticker=ticker,
                            quantity=comp_call_contracts,  # Positive for long
                            strike_price=comp_strike,
                            expiration_date=expiration_date,
                            option_type='call',
                            price=comp_call_price,
                            strategy='dispersion'
                        )
                        premium_spent = comp_call_price * comp_call_contracts * 100
                        total_premium_spent += premium_spent
                        total_long_exposure += call_value
                    
                    if comp_put_contracts > 0:
                        self._open_option_position(
                            ticker=ticker,
                            quantity=comp_put_contracts,  # Positive for long
                            strike_price=comp_strike,
                            expiration_date=expiration_date,
                            option_type='put',
                            price=comp_put_price,
                            strategy='dispersion'
                        )
                        premium_spent = comp_put_price * comp_put_contracts * 100
                        total_premium_spent += premium_spent
                        total_long_exposure += put_value
                    
                except Exception as e:
                    self.logger.error(f"Error trading component {ticker}: {e}")
                    continue
            
            # Deduct the premium spent from our cash
            self.current_cash -= total_premium_spent
            
            # Verify final trade balance
            self.logger.info(f"Total short exposure (index options): ${total_short_exposure:,.2f}")
            self.logger.info(f"Total long exposure (component options): ${total_long_exposure:,.2f}")
            self.logger.info(f"Total premium spent: ${total_premium_spent:,.2f}")
            
            is_balanced = self.risk_manager.check_trade_balance(total_long_exposure, total_short_exposure)
            
            # Log dispersion trade status
            exposure_info = {
                'short_exposure': total_short_exposure,
                'long_exposure': total_long_exposure,
                'premium': total_premium_spent
            }
            self.logger.log_dispersion_trade_status(exposure_info, is_balanced)
            
            if not is_balanced:
                self.logger.warning(f"WARNING: Trade exposure is not balanced. Long/Short ratio: " +
                      f"{total_long_exposure/abs(total_short_exposure):.2f}")
            else:
                self.logger.info("Trade exposure is balanced.")
        else:
            self.logger.info("No component tickers available for dispersion trade")
    
    def _price_option(self, ticker, current_date, expiration_date, strike_price, option_type):
        """Price an option using the configured pricing model"""
        from backtester.options_pricer import price_options
        from datetime import datetime
        
        # Ensure both dates are datetime objects for consistency
        if hasattr(current_date, 'year') and not callable(getattr(current_date, 'date', None)):
            current_date = datetime.combine(current_date, datetime.min.time())
        
        if hasattr(expiration_date, 'year') and not callable(getattr(expiration_date, 'date', None)):
            expiration_date = datetime.combine(expiration_date, datetime.min.time())
        
        try:
            price = price_options(
                ticker=ticker,
                current_date=current_date,
                expiration_date=expiration_date,
                strike_price=strike_price,
                option_type=option_type,
                model=self.config['options']['pricing_model'],
                volatility_method=self.config['options']['volatility_method']
            )
            
            # Ensure price is a valid number
            if np.isnan(price) or np.isinf(price) or price <= 0:
                self.logger.warning(f"Warning: Invalid option price for {ticker} {option_type} (${strike_price}): {price}")
                return 0.01  # Return a small positive value as fallback
            
            return price
        
        except Exception as e:
            self.logger.error(f"Error pricing option {ticker} {option_type} (${strike_price}): {e}")
            return 0.01  # Return a small positive value as fallback
    
    def _open_option_position(self, ticker, quantity, strike_price, expiration_date, 
                             option_type, price, strategy):
        """Open a new option position"""
        import uuid
        
        # Generate a unique position ID
        position_id = str(uuid.uuid4())
        
        # Calculate the total value
        position_value = quantity * price * 100  # 100 shares per contract
        
        # Update cash (negative value for buys, positive for sells)
        self.current_cash -= position_value
        
        # Create position record
        position = {
            'ticker': ticker,
            'type': 'option',
            'option_type': option_type,
            'quantity': quantity,
            'strike_price': strike_price,
            'expiration_date': expiration_date,
            'entry_date': self.current_date,
            'entry_price': price,
            'entry_value': position_value,
            'current_value': position_value,
            'status': 'open',
            'strategy': strategy
        }
        
        # Add to positions dictionary
        self.positions[position_id] = position
        
        # Record the trade
        self._record_trade(
            ticker=ticker,
            trade_type='open',
            position_type='option',
            quantity=quantity,
            price=price,
            value=position_value,
            option_details={
                'strike': strike_price,
                'expiration': expiration_date,
                'option_type': option_type,
                'strategy': strategy
            }
        )
    
    def _add_trading_days(self, date, days):
        """Add a specified number of trading days to a date"""
        # Find the index of the current date in trading_dates
        try:
            current_idx = self.trading_dates.index(date)
        except ValueError:
            # If date is not in trading_dates, find the next trading date
            filtered_dates = [d for d in self.trading_dates if d >= date]
            if not filtered_dates:
                raise ValueError(f"No trading dates after {date}")
            current_idx = self.trading_dates.index(filtered_dates[0])
        
        # Calculate target index
        target_idx = min(current_idx + days, len(self.trading_dates) - 1)
        
        # Return the target date
        return self.trading_dates[target_idx]
    
    def _exit_dispersion_trades(self):
        """Close all open dispersion strategy positions"""
        for position_id, position in list(self.positions.items()):
            if position['status'] == 'open' and position['strategy'] == 'dispersion':
                # Get current market price for this option
                ticker = position['ticker']
                strike = position['strike_price']
                option_type = position['option_type']
                expiration_date = position['expiration_date']
                quantity = position['quantity']
                
                try:
                    # Get current price
                    current_price = self._price_option(
                        ticker=ticker,
                        current_date=self.current_date,
                        expiration_date=expiration_date,
                        strike_price=strike,
                        option_type=option_type
                    )
                    
                    # Calculate value
                    position_value = -quantity * current_price * 100  # Negate quantity to reverse the position
                    
                    # Update cash
                    self.current_cash += position_value
                    
                    # Mark position as closed
                    position['status'] = 'closed'
                    position['exit_date'] = self.current_date
                    position['exit_price'] = current_price
                    position['exit_value'] = position_value
                    
                    # Record the trade
                    self._record_trade(
                        ticker=ticker,
                        trade_type='close',
                        position_type='option',
                        quantity=-quantity,  # Negate to close the position
                        price=current_price,
                        value=position_value,
                        option_details={
                            'strike': strike,
                            'expiration': expiration_date,
                            'option_type': option_type,
                            'strategy': 'dispersion'
                        }
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error closing position {position_id}: {e}")
    
    def _record_trade(self, ticker, trade_type, position_type, quantity, price, value, option_details=None):
        """Record a trade in the trade history"""
        trade = {
            'date': self.current_date,
            'ticker': ticker,
            'trade_type': trade_type,  # 'buy' or 'sell'
            'position_type': position_type,  # 'long' or 'short'
            'quantity': quantity,
            'price': price,
            'value': value,
            'option_details': option_details,
        }
        
        self.trade_history.append(trade)
        
        # Log the trade
        self.logger.log_trade(
            ticker, 
            trade_type, 
            position_type,
            quantity, 
            price, 
            value, 
            option_details
        )
    
    def _record_portfolio_value(self):
        """Record the current portfolio value and risk metrics"""
        # Get risk metrics from risk manager
        drawdown = self.risk_manager.current_drawdown
        risk_status = self.risk_manager.get_status_dict()
        
        # Calculate position metrics
        total_long_exposure = 0
        total_short_exposure = 0
        index_exposure = 0
        components_exposure = 0
        
        for position in self.positions.values():
            if position['status'] == 'open':
                position_value = position['current_value']
                
                # Track long vs short exposure
                if position['quantity'] > 0:
                    total_long_exposure += position_value
                else:
                    total_short_exposure += position_value
                    
                # Track index vs components exposure
                if position['ticker'] == self.index_ticker:
                    index_exposure += position_value
                else:
                    components_exposure += position_value
        
        # Calculate net exposure
        net_exposure = total_long_exposure + total_short_exposure
        net_exposure_pct = net_exposure / self.current_portfolio_value if self.current_portfolio_value != 0 else 0
        
        # Record all metrics
        portfolio_entry = {
            'date': self.current_date,
            'value': self.current_portfolio_value,
            'cash': self.current_cash,
            'drawdown': drawdown,
            'long_exposure': total_long_exposure,
            'short_exposure': total_short_exposure,
            'net_exposure': net_exposure,
            'net_exposure_pct': net_exposure_pct,
            'index_exposure': index_exposure,
            'components_exposure': components_exposure,
            'recovery_mode': risk_status.get('recovery_mode', False)
        }
        
        self.portfolio_history.append(portfolio_entry)
        
        # Log portfolio update
        self.logger.log_portfolio_update(
            self.current_portfolio_value,
            self.current_cash,
            total_long_exposure,
            total_short_exposure,
            drawdown
        )
    
    def _calculate_performance(self):
        """Calculate performance metrics for the backtest"""
        import numpy as np
        import pandas as pd
        
        # Convert portfolio history to DataFrame
        portfolio_df = pd.DataFrame(self.portfolio_history)
        # Now you'll see what columns are available to use instead of 'value'
        portfolio_df['return'] = portfolio_df['value'].pct_change()  # This line will still fail
        
        # Calculate cumulative returns
        portfolio_df['cumulative_return'] = (1 + portfolio_df['return']).cumprod() - 1
        
        # Calculate various metrics
        self.performance_metrics = {
            'total_return': portfolio_df['cumulative_return'].iloc[-1] if not portfolio_df.empty else 0,
            'annualized_return': portfolio_df['return'].mean() * 252 if not portfolio_df.empty else 0,
            'annualized_volatility': portfolio_df['return'].std() * np.sqrt(252) if not portfolio_df.empty else 0,
            'sharpe_ratio': (portfolio_df['return'].mean() / portfolio_df['return'].std() * np.sqrt(252)) 
                           if not portfolio_df.empty and portfolio_df['return'].std() > 0 else 0,
            'max_drawdown': portfolio_df['drawdown'].min() if not portfolio_df.empty else 0,
            'avg_exposure': portfolio_df['net_exposure_pct'].mean() if not portfolio_df.empty else 0,
            'max_exposure': portfolio_df['net_exposure_pct'].max() if not portfolio_df.empty else 0,
            'final_value': portfolio_df['value'].iloc[-1] if not portfolio_df.empty else 0
        }
        
        self.portfolio_df = portfolio_df
    
    def _get_results(self):
        """Get the results of the backtest"""
        return {
            'performance_metrics': self.performance_metrics,
            'portfolio_history': self.portfolio_df,
            'trade_history': pd.DataFrame(self.trade_history)
        }
    
    def plot_results(self):
        """Plot the results of the backtest including risk metrics"""
        import matplotlib.pyplot as plt
        
        # Plot portfolio value over time
        plt.figure(figsize=(12, 16))
        
        # Portfolio value
        plt.subplot(4, 1, 1)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['value'])
        plt.title('Portfolio Value')
        plt.grid(True)
        
        # Cumulative return
        plt.subplot(4, 1, 2)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['cumulative_return'] * 100)
        plt.title('Cumulative Return (%)')
        plt.grid(True)
        
        # Drawdown
        plt.subplot(4, 1, 3)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['drawdown'] * 100)
        plt.axhline(y=self.config['risk_management']['max_drawdown_pct'] * 100, 
                   color='r', linestyle='--', label='Max Drawdown Limit')
        plt.title('Drawdown (%)')
        plt.legend()
        plt.grid(True)
        
        # Exposure metrics
        plt.subplot(4, 1, 4)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['net_exposure_pct'] * 100, 
                label='Net Exposure %')
        plt.axhline(y=self.config['risk_management']['max_portfolio_risk_pct'] * 100, 
                   color='r', linestyle='--', label='Max Risk Limit')
        plt.title('Portfolio Exposure (%)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('results/performance.png')
        
        # Create a second plot for exposure details
        plt.figure(figsize=(12, 10))
        
        # Long vs Short Exposure
        plt.subplot(2, 1, 1)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['long_exposure'], 
                label='Long Exposure', color='green')
        plt.plot(self.portfolio_df['date'], -self.portfolio_df['short_exposure'], 
                label='Short Exposure', color='red')
        plt.title('Long vs Short Exposure ($)')
        plt.legend()
        plt.grid(True)
        
        # Index vs Components Exposure
        plt.subplot(2, 1, 2)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['index_exposure'], 
                label='Index Exposure', color='blue')
        plt.plot(self.portfolio_df['date'], self.portfolio_df['components_exposure'], 
                label='Components Exposure', color='orange')
        plt.title('Index vs Components Exposure ($)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('results/exposure_details.png')
        
        plt.close('all')

    def _enter_reverse_dispersion_trade(self):
        """
        Execute a reverse dispersion trade:
        - Buy index options (pay premium)
        - Sell component options (collect premium)
        
        This is the opposite of a standard dispersion trade, used when
        implied correlation is lower than realized correlation.
        """
        from datetime import timedelta
        
        # 1. Calculate the option parameters - use at least 30 calendar days (about 1 month)
        target_expiry = self.current_date + timedelta(days=30)
        
        # Find the nearest valid trading day to our target expiry
        valid_expiry_days = [d for d in self.trading_dates if d > self.current_date]
        if not valid_expiry_days:
            self.logger.warning(f"No valid expiry dates available after {self.current_date}")
            return
            
        # Use an expiry date that's at least 7 days in the future
        future_dates = [d for d in valid_expiry_days if (d - self.current_date).days >= 7]
        if not future_dates:
            self.logger.warning(f"No valid expiry dates at least 7 days after {self.current_date}")
            return
            
        # Choose the closest date to our target that's at least 7 days out
        min_expiry = future_dates[0]
        expiration_date = min([d for d in future_dates if (d - target_expiry).days >= 0] or [future_dates[-1]])
        
        # Log the expiration we're using
        days_to_expiry = (expiration_date - self.current_date).days
        self.logger.info(f"Setting up reverse trade with {days_to_expiry} days to expiration (from {self.current_date} to {expiration_date})")
        
        # Track exposures
        total_long_exposure = 0
        
        # 2. Long the index option (ATM straddle - both call and put)
        index_price = self._get_price_on_date(self.index_ticker, self.current_date)
        index_strike = round(index_price)
        
        # Price the index options
        try:
            # Price index call
            index_call_price = self._price_option(
                ticker=self.index_ticker,
                current_date=self.current_date,
                expiration_date=expiration_date,
                strike_price=index_strike,
                option_type='call'
            )
            
            # Price index put
            index_put_price = self._price_option(
                ticker=self.index_ticker,
                current_date=self.current_date,
                expiration_date=expiration_date,
                strike_price=index_strike,
                option_type='put'
            )
            
            # Use risk manager to calculate position sizing
            index_call_contracts = self.risk_manager.calculate_position_sizing(
                'reverse_dispersion', 
                self.index_ticker, 
                'call', 
                index_call_price, 
                self.current_portfolio_value
            )
            
            index_put_contracts = self.risk_manager.calculate_position_sizing(
                'reverse_dispersion', 
                self.index_ticker, 
                'put', 
                index_put_price, 
                self.current_portfolio_value
            )
            
            # Check if positions would exceed portfolio risk limits
            call_value = index_call_contracts * index_call_price * 100
            put_value = index_put_contracts * index_put_price * 100
            
            if not self.risk_manager.check_portfolio_risk(call_value + put_value, self.current_portfolio_value):
                self.logger.info("Skipping trade due to portfolio risk limits")
                return
            
            # Execute the index trades (long)
            if index_call_contracts > 0:
                self._open_option_position(
                    ticker=self.index_ticker,
                    quantity=index_call_contracts,  # Positive for long
                    strike_price=index_strike,
                    expiration_date=expiration_date,
                    option_type='call',
                    price=index_call_price,
                    strategy='reverse_dispersion'
                )
                total_long_exposure += call_value
            
            if index_put_contracts > 0:
                self._open_option_position(
                    ticker=self.index_ticker,
                    quantity=index_put_contracts,  # Positive for long
                    strike_price=index_strike,
                    expiration_date=expiration_date,
                    option_type='put',
                    price=index_put_price,
                    strategy='reverse_dispersion'
                )
                total_long_exposure += put_value
            
            # Calculate the total cost of index options
            index_cost = (index_call_price * index_call_contracts + 
                         index_put_price * index_put_contracts) * 100
            
            # Log the amount spent on index options
            self.logger.info(f"Total spent on index options: ${index_cost:,.2f}")
            self.logger.info(f"Total long exposure: ${total_long_exposure:,.2f}")
            
            # If no index options were purchased, exit
            if total_long_exposure <= 0:
                self.logger.info("No index options purchased. Skipping component trades.")
                return
            
            # Use the risk manager to calculate a balanced component budget 
            # Use the balance factor in reverse (1/factor) since this is a reverse trade
            component_premium_target = total_long_exposure / self.risk_manager.long_short_balance_factor
            
        except Exception as e:
            self.logger.error(f"Error pricing index options: {e}")
            return
        
        # 3. Short the component options (ATM straddles)
        if len(self.component_tickers) > 0:
            # Track the total premium collected
            total_premium_collected = 0
            total_short_exposure = 0
            
            # Load component weights from S&P 500 constituents file
            try:
                component_weights = load_index_weights(self.index_ticker)
                self.logger.info(f"Loaded weights for {len(component_weights)} constituents")
                
                # Filter to only include components in our universe
                valid_components = [ticker for ticker in self.component_tickers if ticker in component_weights]
                
                if len(valid_components) < 20:
                    self.logger.warning(f"Warning: Only {len(valid_components)} components with weights. Using top components.")
                    # Sort the component tickers by weight (descending)
                    sorted_components = sorted(
                        component_weights.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    # Take the top 50 components by weight
                    top_components = [comp[0] for comp in sorted_components[:50] 
                                     if comp[0] in self.component_tickers]
                    
                    if len(top_components) > 0:
                        valid_components = top_components
                    else:
                        # Fall back to equal weighting if no components match
                        valid_components = self.component_tickers[:50]
                        component_weights = {ticker: 1.0/len(valid_components) for ticker in valid_components}
                else:
                    # Take top 50 components by weight to focus exposure
                    filtered_weights = {ticker: component_weights[ticker] for ticker in valid_components}
                    sorted_components = sorted(
                        filtered_weights.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )
                    valid_components = [comp[0] for comp in sorted_components[:50]]
                
                # Renormalize weights for selected components
                total_weight = sum(component_weights[ticker] for ticker in valid_components)
                normalized_weights = {
                    ticker: component_weights[ticker] / total_weight for ticker in valid_components
                }
                
                self.logger.info(f"Trading with {len(valid_components)} weighted components")
                
            except Exception as e:
                self.logger.error(f"Error loading component weights: {e}. Using equal weighting.")
                valid_components = self.component_tickers[:50]  # Limit to 50 components
                normalized_weights = {ticker: 1.0/len(valid_components) for ticker in valid_components}
            
            # Allocate the premium target across components based on their weights
            premium_target_per_component = {
                ticker: component_premium_target * normalized_weights[ticker]
                for ticker in valid_components
            }
            
            # Log the weighted allocation
            self.logger.info(f"Total target premium to collect: ${component_premium_target:,.2f}")
            
            for ticker in valid_components:
                try:
                    comp_price = self._get_price_on_date(ticker, self.current_date)
                    comp_strike = round(comp_price)
                    
                    target_premium = premium_target_per_component[ticker]
                    self.logger.info(f"Target premium for {ticker} (weight {normalized_weights[ticker]:.2%}): ${target_premium:,.2f}")
                    
                    # Price component call
                    comp_call_price = self._price_option(
                        ticker=ticker,
                        current_date=self.current_date,
                        expiration_date=expiration_date,
                        strike_price=comp_strike,
                        option_type='call'
                    )
                    
                    # Price component put
                    comp_put_price = self._price_option(
                        ticker=ticker,
                        current_date=self.current_date,
                        expiration_date=expiration_date,
                        strike_price=comp_strike,
                        option_type='put'
                    )
                    
                    # Calculate contracts needed to reach premium target (split between call and put)
                    target_call_contracts = int(target_premium / 2 / (comp_call_price * 100))
                    target_put_contracts = int(target_premium / 2 / (comp_put_price * 100))
                    
                    # Ensure minimum of 1 contract if target is positive
                    if target_call_contracts == 0 and target_premium > 0:
                        target_call_contracts = 1
                    if target_put_contracts == 0 and target_premium > 0:
                        target_put_contracts = 1
                    
                    # Limit by risk manager
                    risk_call_contracts = self.risk_manager.calculate_position_sizing(
                        'reverse_dispersion', 
                        ticker, 
                        'call', 
                        comp_call_price, 
                        self.current_portfolio_value * normalized_weights[ticker]
                    )
                    
                    risk_put_contracts = self.risk_manager.calculate_position_sizing(
                        'reverse_dispersion', 
                        ticker, 
                        'put', 
                        comp_put_price, 
                        self.current_portfolio_value * normalized_weights[ticker]
                    )
                    
                    # Use the minimum of target and risk-based sizing
                    comp_call_contracts = min(target_call_contracts, risk_call_contracts)
                    comp_put_contracts = min(target_put_contracts, risk_put_contracts)
                    
                    # Check if positions would exceed portfolio risk limits
                    call_value = -comp_call_contracts * comp_call_price * 100  # Negative for short
                    put_value = -comp_put_contracts * comp_put_price * 100     # Negative for short
                    
                    if not self.risk_manager.check_portfolio_risk(call_value + put_value, self.current_portfolio_value):
                        self.logger.info(f"Skipping {ticker} component trade due to portfolio risk limits")
                        continue
                    
                    # Execute the component trades (short)
                    if comp_call_contracts > 0:
                        self._open_option_position(
                            ticker=ticker,
                            quantity=-comp_call_contracts,  # Negative for short
                            strike_price=comp_strike,
                            expiration_date=expiration_date,
                            option_type='call',
                            price=comp_call_price,
                            strategy='reverse_dispersion'
                        )
                        premium_collected = comp_call_price * comp_call_contracts * 100
                        total_premium_collected += premium_collected
                        total_short_exposure += call_value
                    
                    if comp_put_contracts > 0:
                        self._open_option_position(
                            ticker=ticker,
                            quantity=-comp_put_contracts,  # Negative for short
                            strike_price=comp_strike,
                            expiration_date=expiration_date,
                            option_type='put',
                            price=comp_put_price,
                            strategy='reverse_dispersion'
                        )
                        premium_collected = comp_put_price * comp_put_contracts * 100
                        total_premium_collected += premium_collected
                        total_short_exposure += put_value
                    
                except Exception as e:
                    self.logger.error(f"Error trading component {ticker}: {e}")
                    continue
            
            # Add the premium collected to our cash
            self.current_cash += total_premium_collected
            
            # Verify final trade balance
            self.logger.info(f"Total long exposure (index options): ${total_long_exposure:,.2f}")
            self.logger.info(f"Total short exposure (component options): ${total_short_exposure:,.2f}")
            self.logger.info(f"Total premium collected: ${total_premium_collected:,.2f}")
            
            is_balanced = self.risk_manager.check_trade_balance(total_long_exposure, total_short_exposure)
            
            # Log dispersion trade status
            exposure_info = {
                'short_exposure': total_short_exposure,
                'long_exposure': total_long_exposure,
                'premium': total_premium_collected
            }
            self.logger.log_dispersion_trade_status(exposure_info, is_balanced)
            
            if not is_balanced:
                self.logger.warning(f"WARNING: Trade exposure is not balanced. Long/Short ratio: " +
                      f"{total_long_exposure/abs(total_short_exposure):.2f}")
            else:
                self.logger.info("Trade exposure is balanced.")
        else:
            self.logger.info("No component tickers available for reverse dispersion trade")

    def _close_position(self, position_id, position, reason="manual"):
        """Close a position at current market price"""
        if position['status'] != 'open':
            return
            
        ticker = position['ticker']
        strike = position['strike_price']
        option_type = position['option_type']
        expiration_date = position['expiration_date']
        quantity = position['quantity']
        
        try:
            # Get current price
            current_price = self._price_option(
                ticker=ticker,
                current_date=self.current_date,
                expiration_date=expiration_date,
                strike_price=strike,
                option_type=option_type
            )
            
            # Calculate value
            position_value = -quantity * current_price * 100  # Negate quantity to reverse the position
            
            # Update cash
            self.current_cash += position_value
            
            # Mark position as closed
            position['status'] = 'closed'
            position['exit_date'] = self.current_date
            position['exit_price'] = current_price
            position['exit_value'] = position_value
            position['exit_reason'] = reason
            
            # Record the trade
            self._record_trade(
                ticker=ticker,
                trade_type='close',
                position_type='option',
                quantity=-quantity,  # Negate to close the position
                price=current_price,
                value=position_value,
                option_details={
                    'strike': strike,
                    'expiration': expiration_date,
                    'option_type': option_type,
                    'strategy': position['strategy'],
                    'exit_reason': reason
                }
            )
            
            self.logger.info(f"Closed position {position_id} ({ticker} {option_type}) due to {reason}")
            
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {e}")

    def _close_all_positions(self, reason="risk_limit"):
        """Close all open positions"""
        self.logger.warning(f"CLOSING ALL POSITIONS due to {reason}")
        for position_id, position in list(self.positions.items()):
            if position['status'] == 'open':
                self._close_position(position_id, position, reason=reason)
