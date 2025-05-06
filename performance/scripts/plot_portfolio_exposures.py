import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import argparse

def plot_portfolio_history(csv_path, start_date=None, end_date=None, dspx_path='DSPX_History.csv'):
    # Read the portfolio CSV file
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Read DSPX data if provided
    if dspx_path:
        dspx_df = pd.read_csv(dspx_path)
        dspx_df['date'] = pd.to_datetime(dspx_df['DATE'], format='%m/%d/%Y')
        dspx_df = dspx_df.rename(columns={'DSPX': 'dspx'})
    
    # Filter by date range if provided
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
        if dspx_path:
            dspx_df = dspx_df[dspx_df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
        if dspx_path:
            dspx_df = dspx_df[dspx_df['date'] <= pd.to_datetime(end_date)]
    
    # Create figure and subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[1, 1])
    fig.suptitle('Portfolio Analysis', fontsize=14)
    
    # Plot 1: Portfolio Value and DSPX
    ax1_portfolio = ax1
    ax1_portfolio.plot(df['date'], df['value'], label='Portfolio Value', color='blue')
    ax1_portfolio.set_ylabel('Portfolio Value ($)', color='blue')
    ax1_portfolio.tick_params(axis='y', labelcolor='blue')
    
    if dspx_path:
        # Create a second y-axis for DSPX
        ax1_dspx = ax1_portfolio.twinx()
        ax1_dspx.plot(dspx_df['date'], dspx_df['dspx'], label='DSPX', color='red', alpha=0.7)
        ax1_dspx.set_ylabel('DSPX', color='red')
        ax1_dspx.tick_params(axis='y', labelcolor='red')
        
        # Add both legends
        lines1, labels1 = ax1_portfolio.get_legend_handles_labels()
        lines2, labels2 = ax1_dspx.get_legend_handles_labels()
        ax1_dspx.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    else:
        ax1_portfolio.legend(loc='upper left')
    
    ax1_portfolio.grid(True, alpha=0.3)
    ax1_portfolio.set_title('Portfolio Value and DSPX Over Time')
    
    # Plot 2: Exposures
    ax2.plot(df['date'], df['index_exposure'], label='Index Exposure', color='red')
    ax2.plot(df['date'], df['components_exposure'], label='Components Exposure', color='green')
    ax2.plot(df['date'], df['net_exposure'], label='Net Exposure', color='black', linestyle='--')
    ax2.set_title('Portfolio Exposures')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Exposure ($)')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    
    # Format x-axis dates
    plt.gcf().autofmt_xdate()
    
    # Adjust layout to prevent overlap
    plt.tight_layout()
    
    return fig

def main():
    parser = argparse.ArgumentParser(description='Plot portfolio history from CSV file')
    parser.add_argument('csv_path', type=str, help='Path to the portfolio history CSV file')
    parser.add_argument('--dspx_path', type=str, help='Path to the DSPX history CSV file', required=False)
    parser.add_argument('--start_date', type=str, help='Start date (YYYY-MM-DD)', required=False)
    parser.add_argument('--end_date', type=str, help='End date (YYYY-MM-DD)', required=False)
    parser.add_argument('--output', type=str, help='Output file path', required=False)
    
    args = parser.parse_args()
    
    # Create the plot
    fig = plot_portfolio_history(args.csv_path, args.start_date, args.end_date, args.dspx_path)
    
    # Save or show the plot
    if args.output:
        fig.savefig(args.output, bbox_inches='tight', dpi=300)
        print(f"Plot saved to {args.output}")
    else:
        plt.show()

if __name__ == "__main__":
    main()