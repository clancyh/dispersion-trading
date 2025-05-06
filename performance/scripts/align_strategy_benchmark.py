import pandas as pd
import os

def align_data_with_benchmark():
    """
    Aligns the combined portfolio history with SPY benchmark data.
    Fills missing portfolio dates using interpolation based on SPY dates.
    Calculates a benchmark value series for SPY starting at the same initial capital.
    Saves a CSV with date, aligned portfolio value, and SPY benchmark value.
    """
    try:
        # Determine workspace root based on the script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workspace_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

        # Define paths
        results_path_dir = os.path.join(workspace_root, "results")
        data_processed_path_dir = os.path.join(workspace_root, "data", "processed")

        portfolio_history_path = os.path.join(results_path_dir, "combined_portfolio_history.csv")
        spy_path = os.path.join(data_processed_path_dir, "SPY.csv")
        output_path = os.path.join(results_path_dir, "aligned_strategy_and_benchmark.csv")

        initial_portfolio_value = 1_000_000

        # --- Load and Prepare Portfolio Data ---
        print(f"Loading portfolio history from: {portfolio_history_path}")
        portfolio_df = pd.read_csv(portfolio_history_path)
        if portfolio_df.empty:
            print(f"Warning: Portfolio history file {portfolio_history_path} is empty.")
            # Fallback: create an empty DataFrame to avoid subsequent errors if possible
            portfolio_df = pd.DataFrame(columns=['date', 'continuous_portfolio_value'])
        
        portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
        portfolio_df = portfolio_df.set_index('date')[['continuous_portfolio_value']].sort_index()

        # --- Load and Prepare SPY Data & Benchmark ---
        print(f"Loading SPY data from: {spy_path}")
        spy_df = pd.read_csv(spy_path, usecols=['date', 'Adjusted'])
        if spy_df.empty:
            print(f"Warning: SPY data file {spy_path} is empty.")
            spy_df = pd.DataFrame(columns=['date', 'Adjusted'])

        spy_df['date'] = pd.to_datetime(spy_df['date'])
        spy_df = spy_df.set_index('date').sort_index()
        spy_df.rename(columns={'Adjusted': 'spy_price'}, inplace=True)
        
        if spy_df.empty or 'spy_price' not in spy_df.columns or spy_df['spy_price'].isnull().all():
             print("SPY data is empty or lacks 'spy_price' data. SPY benchmark value will be set to initial value or NaN.")
             spy_df['spy_benchmark_value'] = initial_portfolio_value 
        else:
            spy_daily_returns = spy_df['spy_price'].pct_change().fillna(0.0)
            
            spy_eod_values = []
            current_benchmark_val = initial_portfolio_value 
            if not spy_daily_returns.empty:
                # First EOD value based on first day's return (0.0 after fillna)
                current_benchmark_val *= (1 + spy_daily_returns.iloc[0]) 
                spy_eod_values.append(current_benchmark_val)
                
                # For subsequent days
                for daily_return in spy_daily_returns.iloc[1:]:
                    current_benchmark_val *= (1 + daily_return)
                    spy_eod_values.append(current_benchmark_val)
                
                # Ensure series alignment if spy_daily_returns was very short
                if len(spy_eod_values) == len(spy_daily_returns.index):
                    spy_df['spy_benchmark_value'] = pd.Series(spy_eod_values, index=spy_daily_returns.index)
                elif len(spy_daily_returns.index) == 1: # Only one SPY data point after pct_change
                     spy_df['spy_benchmark_value'] = initial_portfolio_value
                else: # Fallback or error
                    print("Warning: Mismatch in length for SPY benchmark calculation. Filling with initial value.")
                    spy_df['spy_benchmark_value'] = initial_portfolio_value
            else: 
                spy_df['spy_benchmark_value'] = initial_portfolio_value

        # --- Align Portfolio Data to SPY's Date Index ---
        if portfolio_df.empty or portfolio_df['continuous_portfolio_value'].isnull().all():
            print("Portfolio data is empty or all NaNs. Aligned portfolio value will be set to initial value.")
            aligned_portfolio_values = pd.Series(initial_portfolio_value, index=spy_df.index, dtype=float)
        else:
            aligned_portfolio_values = portfolio_df['continuous_portfolio_value'].reindex(spy_df.index)
            aligned_portfolio_values = aligned_portfolio_values.interpolate(method='linear')
            aligned_portfolio_values = aligned_portfolio_values.bfill() # Fill NaNs at the beginning
            aligned_portfolio_values = aligned_portfolio_values.ffill() # Fill NaNs at the end

        # Final check for any remaining NaNs in portfolio_value (e.g., if SPY index was empty)
        if spy_df.index.empty:
             aligned_portfolio_values = pd.Series(dtype=float) # Empty series if SPY index is empty
        else:
            aligned_portfolio_values.fillna(initial_portfolio_value, inplace=True)


        # --- Create and Save Final Combined DataFrame ---
        final_df = pd.DataFrame(index=spy_df.index)
        final_df['portfolio_value'] = aligned_portfolio_values
        final_df['spy_benchmark_value'] = spy_df.get('spy_benchmark_value', pd.Series(initial_portfolio_value, index=spy_df.index))
        
        # If spy_benchmark_value column ended up all NaNs or missing, fill with initial_value
        if 'spy_benchmark_value' not in final_df or final_df['spy_benchmark_value'].isnull().all():
            final_df['spy_benchmark_value'] = initial_portfolio_value


        final_df.to_csv(output_path)
        print(f"Successfully saved aligned strategy and benchmark data to {output_path}")

    except FileNotFoundError as fnf_error:
        print(f"Error: A required file was not found. {fnf_error}")
    except pd.errors.EmptyDataError as ede_error:
        print(f"Error: A CSV file is empty. {ede_error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    align_data_with_benchmark() 