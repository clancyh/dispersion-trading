import pandas as pd
import os

def combine_portfolio_histories():
    """
    Combines portfolio history CSVs from different backtest periods,
    calculates a continuous portfolio value, and saves the result.
    """
    base_results_path = "results" # Relative to the script's location
    output_file_path = os.path.join(base_results_path, "combined_portfolio_history.csv")

    # Define the order of directories and their paths
    # Assuming the backtests should be processed in chronological order
    backtest_dirs_info = [
        {"name": "2020 BT", "path_segment": "2020 BT"},
        {"name": "2021", "path_segment": "2021_BT"},
        {"name": "2022", "path_segment": "2022_BT"},
        {"name": "2023-24", "path_segment": "2023-24 BT"}
    ]

    all_dfs = []

    for bt_info in backtest_dirs_info:
        file_path = os.path.join(base_results_path, bt_info["path_segment"], "portfolio_history.csv")
        if os.path.exists(file_path):
            print(f"Reading {file_path}...")
            df = pd.read_csv(file_path)
            # Assuming 'date' column exists for sorting and 'return' for calculations
            if 'date' not in df.columns or 'return' not in df.columns:
                print(f"Warning: 'date' or 'return' column missing in {file_path}. Skipping this file.")
                continue
            all_dfs.append(df)
        else:
            print(f"Warning: {file_path} not found. Skipping.")

    if not all_dfs:
        print("No portfolio history files were found or read. Exiting.")
        return

    # Concatenate all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # Convert 'date' column to datetime objects and sort
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    combined_df = combined_df.sort_values(by='date').reset_index(drop=True)

    # Fill NaN values in the 'return' column with 0.0 to prevent calculation errors
    combined_df['return'] = combined_df['return'].fillna(0.0)

    # Calculate continuous portfolio value
    initial_portfolio_value = 1_000_000

    if not combined_df.empty:
        # The user stated: "use the daily return column to appreciate that value through all the years."
        # This implies we track the value as it grows.
        # Let's store the portfolio value *after* each day's return is accounted for.

        # Initial value before any returns
        # The problem states "appreciate that value".
        # So, if first row date D1 has return R1, value becomes 1M * (1+R1)
        # If second row date D2 has return R2, value becomes (1M * (1+R1)) * (1+R2)

        current_portfolio_value = initial_portfolio_value
        calculated_portfolio_values = []

        # The loop iterates over the 'return' column from the combined dataframe.
        # The variable 'daily_return_value' here takes each value from the 'return' column.
        for daily_return_value in combined_df['return']:
            current_portfolio_value *= (1 + daily_return_value)
            calculated_portfolio_values.append(current_portfolio_value)
        
        # Create the new DataFrame with only the desired columns
        final_df = pd.DataFrame({
            'date': combined_df['date'],  # Dates are already sorted
            'continuous_portfolio_value': calculated_portfolio_values
        })

    else:
        # If combined_df was empty from the start, create an empty DataFrame with the correct columns
        final_df = pd.DataFrame(columns=['date', 'continuous_portfolio_value'])

    # Save the final simplified dataframe
    try:
        final_df.to_csv(output_file_path, index=False)
        print(f"Successfully saved simplified portfolio history to {output_file_path}")
    except Exception as e:
        print(f"Error saving simplified portfolio history: {e}")

if __name__ == "__main__":
    combine_portfolio_histories() 