import pandas as pd
import os
from datetime import datetime, timedelta
from backtester.correlation import calculate_correlation_dispersion
from backtester.options_pricer import price_options
import numpy as np

class BacktestEngine:
    def __init__(self, config):
        # Load configuration
        self.config = config
        self.start_date = config['backtest']['start_date']
        self.end_date = config['backtest']['end_date']
        self.initial_cash = config['portfolio']['initial_cash']
        
        # Portfolio state
        self.current_date = None
        self.current_cash = self.initial_cash
        self.positions = {}  # Will hold all option and stock positions
        
        # Performance tracking
        self.portfolio_history = []  # Daily portfolio values
        self.trade_history = []      # Record of all trades
        
        # Initialize data
        self._load_data()
        
    def _load_data(self):
        """Load all required data for backtesting"""
        # Get the universe of stocks
        self.index_ticker = self.config['universe']['index']
        # Load selected component tickers
        from backtester.universe import selected_tickers
        self.component_tickers = selected_tickers
        
        # Load price data
        self._load_price_data()
        
        # Build a calendar of trading dates
        self._build_date_range()
        
    def _load_price_data(self):
        """Load price data for index and all component stocks"""
        import pandas as pd
        import os
        
        self.price_data = {}
        
        # Load index data
        index_file = f"data/processed/{self.index_ticker}.csv"
        if os.path.exists(index_file):
            self.price_data[self.index_ticker] = pd.read_csv(index_file)
            self.price_data[self.index_ticker]['date'] = pd.to_datetime(self.price_data[self.index_ticker]['date'])
        
        # Load component data
        for ticker in self.component_tickers:
            ticker_file = f"data/processed/{ticker}.csv"
            if os.path.exists(ticker_file):
                self.price_data[ticker] = pd.read_csv(ticker_file)
                self.price_data[ticker]['date'] = pd.to_datetime(self.price_data[ticker]['date'])
        
        # Load VIX data for implied volatility
        vix_file = f"data/processed/^VIX.csv"
        if os.path.exists(vix_file):
            self.price_data["^VIX"] = pd.read_csv(vix_file)
            self.price_data["^VIX"]['date'] = pd.to_datetime(self.price_data["^VIX"]['date'])
    
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
        print(f"Starting backtest from {self.start_date} to {self.end_date}")
        print(f"Trading universe: {self.index_ticker} and {len(self.component_tickers)} components")
        
        # Initialize portfolio
        self.current_cash = self.initial_cash
        self.positions = {}
        self.portfolio_history = []
        self.trade_history = []
        
        # Iterate through each trading day
        for date in self.trading_dates:
            self.current_date = date
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
        
        # 3. Generate trading signals
        signals = self._generate_signals()
        
        # 4. Execute trades based on signals
        if signals:
            self._execute_trades(signals)
        
        # 5. Record end-of-day portfolio value
        self._record_portfolio_value()
    
    def _update_position_values(self):
        """Update the value of all open positions"""
        # For each position, calculate its current market value
        portfolio_value = self.current_cash
        
        for position_id, position in self.positions.items():
            # If the position is still open
            if position['status'] == 'open':
                current_value = self._calculate_position_value(position)
                position['current_value'] = current_value
                portfolio_value += current_value
        
        self.current_portfolio_value = portfolio_value
    
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
                print(f"Error pricing option {position_id}: {e}")
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
    
    def _generate_signals(self):
        """Generate trading signals based on dispersion strategy"""
        from backtester.correlation import calculate_correlation_dispersion
        from datetime import datetime
        
        # Skip if we don't have enough components
        if len(self.component_tickers) <= 1:
            return None
        
        try:
            # Convert date to datetime for proper comparison
            current_datetime = datetime.combine(self.current_date, datetime.min.time())
            
            # Calculate dispersion metrics
            metrics = calculate_correlation_dispersion(
                self.index_ticker, 
                self.component_tickers, 
                current_datetime,  # Use datetime instead of date
                lookback=self.config['options']['volatility_lookback']
            )
            
            # Get thresholds from config
            entry_threshold = self.config['dispersion']['entry_threshold']
            exit_threshold = self.config['dispersion']['exit_threshold']
            
            dispersion = metrics['correlation_dispersion']
            
            # Check for signals
            if dispersion > entry_threshold:
                # High implied correlation relative to realized
                # Sell index options, buy component options
                return {
                    'signal': 'ENTER_DISPERSION',
                    'action': 'SELL_INDEX_BUY_COMPONENTS',
                    'metrics': metrics
                }
            elif dispersion < -entry_threshold:
                # Low implied correlation relative to realized
                # Buy index options, sell component options
                return {
                    'signal': 'ENTER_REVERSE_DISPERSION',
                    'action': 'BUY_INDEX_SELL_COMPONENTS',
                    'metrics': metrics
                }
            elif abs(dispersion) < exit_threshold and self._has_open_dispersion_positions():
                # Correlation gap has closed - exit positions
                return {
                    'signal': 'EXIT',
                    'action': 'CLOSE_POSITIONS',
                    'metrics': metrics
                }
            
        except Exception as e:
            print(f"Error generating signals on {self.current_date}: {e}")
        
        return None
    
    def _has_open_dispersion_positions(self):
        """Check if there are open dispersion positions"""
        for position in self.positions.values():
            if position['status'] == 'open' and position['strategy'] == 'dispersion':
                return True
        return False
    
    def _execute_trades(self, signal):
        """Execute trades based on the signal"""
        # Implementation will vary based on your specific strategy requirements
        if signal['signal'] == 'ENTER_DISPERSION':
            self._enter_dispersion_trade()
        elif signal['signal'] == 'ENTER_REVERSE_DISPERSION':
            self._enter_reverse_dispersion_trade()
        elif signal['signal'] == 'EXIT':
            self._exit_dispersion_trades()
    
    def _enter_dispersion_trade(self):
        """
        Execute a dispersion trade:
        - Sell index options (collect premium)
        - Buy component options (pay premium)
        """
        from datetime import timedelta
        
        # 1. Calculate the option parameters - use 30 calendar days (about 1 month)
        target_expiry = self.current_date + timedelta(days=30)
        
        # Find the nearest valid trading day to our target expiry
        valid_expiry_days = [d for d in self.trading_dates if d >= target_expiry]
        if valid_expiry_days:
            expiration_date = valid_expiry_days[0]  # First trading day on/after our target
        else:
            # If we're near the end of our data, use the last trading day
            expiration_date = self.trading_dates[-1]
        
        # Log the expiration we're using
        days_to_expiry = (expiration_date - self.current_date).days
        print(f"Setting up trade with {days_to_expiry} days to expiration (from {self.current_date} to {expiration_date})")
        
        # 2. Short the index option (ATM straddle - both call and put)
        index_price = self._get_price_on_date(self.index_ticker, self.current_date)
        index_strike = round(index_price)  # Rounded to nearest whole number
        
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
            
            # Calculate quantities safely
            index_capital = self.current_portfolio_value * 0.5  # Allocate half to short index options
            
            # Safe calculation for call contracts
            if index_call_price > 0:
                index_call_contracts = max(0, int(index_capital / (index_call_price * 100) / 2))
            else:
                index_call_contracts = 0
                print(f"Warning: Zero or invalid call price for {self.index_ticker}")
            
            # Safe calculation for put contracts
            if index_put_price > 0:
                index_put_contracts = max(0, int(index_capital / (index_put_price * 100) / 2))
            else:
                index_put_contracts = 0
                print(f"Warning: Zero or invalid put price for {self.index_ticker}")
            
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
            
            # Update remaining budget
            premium_collected = (index_call_price * index_call_contracts + 
                                index_put_price * index_put_contracts) * 100
            self.current_cash += premium_collected
            
        except Exception as e:
            print(f"Error pricing index options: {e}")
            return
        
        # 3. Long the component options (ATM straddles)
        # Calculate equal allocation for each component
        if len(self.component_tickers) > 0:
            component_budget = self.current_portfolio_value * 0.5  # Allocate half to component options
            
            for ticker in self.component_tickers:
                try:
                    comp_price = self._get_price_on_date(ticker, self.current_date)
                    comp_strike = round(comp_price)
                    
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
                    
                    # Safe calculation for component calls
                    if comp_call_price > 0:
                        comp_call_contracts = max(0, int(component_budget / (comp_call_price * 100) / 2))
                    else:
                        comp_call_contracts = 0
                        print(f"Warning: Zero or invalid call price for {ticker}")
                    
                    # Safe calculation for component puts
                    if comp_put_price > 0:
                        comp_put_contracts = max(0, int(component_budget / (comp_put_price * 100) / 2))
                    else:
                        comp_put_contracts = 0
                        print(f"Warning: Zero or invalid put price for {ticker}")
                    
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
                    
                except Exception as e:
                    print(f"Error trading component {ticker}: {e}")
                    continue
    
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
                print(f"Warning: Invalid option price for {ticker} {option_type} (${strike_price}): {price}")
                return 0.01  # Return a small positive value as fallback
            
            return price
        
        except Exception as e:
            print(f"Error pricing option {ticker} {option_type} (${strike_price}): {e}")
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
                    print(f"Error closing position {position_id}: {e}")
    
    def _record_trade(self, ticker, trade_type, position_type, quantity, price, value, option_details=None):
        """Record a trade in the trade history"""
        trade = {
            'date': self.current_date,
            'ticker': ticker,
            'trade_type': trade_type,  # 'open' or 'close'
            'position_type': position_type,  # 'stock' or 'option'
            'quantity': quantity,
            'price': price,
            'value': value
        }
        
        if option_details:
            trade.update(option_details)
        
        self.trade_history.append(trade)
    
    def _record_portfolio_value(self):
        """Record the current portfolio value"""
        self.portfolio_history.append({
            'date': self.current_date,
            'value': self.current_portfolio_value
        })
    
    def _calculate_performance(self):
        """Calculate performance metrics for the backtest"""
        import numpy as np
        import pandas as pd
        
        # Convert portfolio history to DataFrame
        portfolio_df = pd.DataFrame(self.portfolio_history)
        
        # Calculate returns
        portfolio_df['return'] = portfolio_df['value'].pct_change()
        
        # Calculate cumulative returns
        portfolio_df['cumulative_return'] = (1 + portfolio_df['return']).cumprod() - 1
        
        # Calculate drawdowns
        portfolio_df['peak'] = portfolio_df['value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['value'] - portfolio_df['peak']) / portfolio_df['peak']
        
        # Calculate various metrics
        self.performance_metrics = {
            'total_return': portfolio_df['cumulative_return'].iloc[-1],
            'annualized_return': portfolio_df['return'].mean() * 252,
            'annualized_volatility': portfolio_df['return'].std() * np.sqrt(252),
            'sharpe_ratio': portfolio_df['return'].mean() / portfolio_df['return'].std() * np.sqrt(252),
            'max_drawdown': portfolio_df['drawdown'].min(),
            'final_value': portfolio_df['value'].iloc[-1]
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
        """Plot the results of the backtest"""
        import matplotlib.pyplot as plt
        
        # Plot portfolio value over time
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 1, 1)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['value'])
        plt.title('Portfolio Value')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.plot(self.portfolio_df['date'], self.portfolio_df['cumulative_return'] * 100)
        plt.title('Cumulative Return (%)')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('results/performance.png')
        plt.close()

    def _enter_reverse_dispersion_trade(self):
        """
        Execute a reverse dispersion trade:
        - Buy index options (pay premium)
        - Sell component options (collect premium)
        
        This is the opposite of a standard dispersion trade, used when
        implied correlation is lower than realized correlation.
        """
        # 1. Calculate the option parameters
        expiration_days = self.config['options']['max_days_to_expiry']
        expiration_date = self._add_trading_days(self.current_date, expiration_days)
        
        # Calculate position size using a percentage of portfolio
        position_size = self.current_portfolio_value * self.config['dispersion']['max_position_size']
        remaining_budget = position_size
        
        # 2. Long the index option (ATM straddle - both call and put)
        index_price = self._get_price_on_date(self.index_ticker, self.current_date)
        index_strike = round(index_price)  # Rounded to nearest whole number
        
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
            
            # Calculate quantities (LONG index options)
            index_capital = position_size * 0.5  # Allocate half to long index options
            index_call_contracts = int(index_capital / (index_call_price * 100) / 2)  # Half to calls
            index_put_contracts = int(index_capital / (index_put_price * 100) / 2)    # Half to puts
            
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
            
            # Update remaining budget (spent money on index options)
            index_cost = (index_call_price * index_call_contracts + 
                         index_put_price * index_put_contracts) * 100
            remaining_budget = position_size - index_cost
            
        except Exception as e:
            print(f"Error pricing index options: {e}")
            return
        
        # 3. Short the component options (ATM straddles)
        # Calculate equal allocation for each component
        if len(self.component_tickers) > 0:
            # We'll collect premium here, so it's about risk management
            # Limit the number of short contracts based on remaining budget
            component_risk_allocation = remaining_budget / len(self.component_tickers)
            
            for ticker in self.component_tickers:
                try:
                    comp_price = self._get_price_on_date(ticker, self.current_date)
                    comp_strike = round(comp_price)
                    
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
                    
                    # Safe calculation for component calls
                    if comp_call_price > 0:
                        comp_call_contracts = max(0, int(component_risk_allocation / (comp_call_price * 100) / 2))
                    else:
                        comp_call_contracts = 0
                        print(f"Warning: Zero or invalid call price for {ticker}")
                    
                    # Safe calculation for component puts
                    if comp_put_price > 0:
                        comp_put_contracts = max(0, int(component_risk_allocation / (comp_put_price * 100) / 2))
                    else:
                        comp_put_contracts = 0
                        print(f"Warning: Zero or invalid put price for {ticker}")
                    
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
                    
                except Exception as e:
                    print(f"Error trading component {ticker}: {e}")
                    continue
