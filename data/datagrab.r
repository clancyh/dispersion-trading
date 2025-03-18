#!/usr/bin/env Rscript

# =====================================================
# datagrab.r - Simple Historical Data Grabber
# =====================================================

# Install required packages if not already installed
required_packages <- c("quantmod", "xts", "zoo")
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
if(length(new_packages)) install.packages(new_packages)

# Load required libraries
suppressPackageStartupMessages({
  library(quantmod)  # For financial data acquisition
  library(xts)       # For time series objects
  library(zoo)       # For time series objects
})

# =====================================================
# Data Acquisition Function
# =====================================================

# Fetch stock data from Yahoo Finance
get_stock_data <- function(symbols, start_date, end_date, adjust = TRUE) {
  # Convert to proper date format
  start_date <- as.Date(start_date, format="%Y-%m-%d")
  end_date <- as.Date(end_date, format="%Y-%m-%d")
  
  # Initialize results container
  data_list <- list()
  
  # Fetch data for each symbol
  for (symbol in symbols) {
    tryCatch({
      cat(sprintf("Fetching data for %s...\n", symbol))
      
      # Get data from Yahoo Finance
      data <- getSymbols(symbol, src = "yahoo", 
                       from = start_date, 
                       to = end_date, 
                       auto.assign = FALSE,
                       adjust = adjust)
      
      # Rename columns to have consistent naming
      colnames(data) <- c("Open", "High", "Low", "Close", "Volume", "Adjusted")
      
      # Add to list
      data_list[[symbol]] <- data
      
    }, error = function(e) {
      warning(sprintf("Error fetching data for %s: %s", symbol, e$message))
    })
  }
  
  return(data_list)
}

# =====================================================
# Data Export Function
# =====================================================

# Export data to CSV files
export_to_csv <- function(data_list, output_dir = "data/processed") {
  # Create output directory if it doesn't exist
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE)
  }
  
  # Export each data frame to CSV
  for (name in names(data_list)) {
    file_path <- file.path(output_dir, paste0(name, ".csv"))
    write.csv(data.frame(date = index(data_list[[name]]), 
                        coredata(data_list[[name]])), 
             file = file_path, row.names = FALSE)
    cat(sprintf("Exported %s to %s\n", name, file_path))
  }
}

# =====================================================
# Main Function
# =====================================================

# Main function to grab data
grab_data <- function(symbols = c("SPY", "QQQ", "IWM"),
                     start_date = Sys.Date() - 365,
                     end_date = Sys.Date()) {
  
  # Fetch stock data
  cat("Fetching stock data...\n")
  stock_data <- get_stock_data(symbols, start_date, end_date)
  
  # Export data as CSV
  export_to_csv(stock_data)
  
  return(stock_data)
}

# =====================================================
# Command Line Interface
# =====================================================

# Run as a command line script if not being sourced
if (!interactive()) {
  # Parse command line arguments
  args <- commandArgs(trailingOnly = TRUE)
  
  # Check for help flag
  if (length(args) > 0 && args[1] %in% c("-h", "--help")) {
    cat("Usage: Rscript datagrab.r [symbols] [start_date] [end_date]\n")
    cat("\n")
    cat("Arguments:\n")
    cat("  symbols    - Comma-separated list of ticker symbols (default: SPY,QQQ,IWM)\n")
    cat("  start_date - Start date in YYYY-MM-DD format (default: 1 year ago)\n")
    cat("  end_date   - End date in YYYY-MM-DD format (default: today)\n")
    quit(status = 0)
  }
  
  # Process arguments
  symbols <- if (length(args) >= 1) strsplit(args[1], ",")[[1]] else c("SPY", "QQQ", "IWM")
  start_date <- if (length(args) >= 2) as.Date(args[2], format="%Y-%m-%d") else Sys.Date() - 365
  end_date <- if (length(args) >= 3) as.Date(args[3], format="%Y-%m-%d") else Sys.Date()
  
  # Run the main function
  result <- grab_data(
    symbols = symbols,
    start_date = start_date,
    end_date = end_date
  )
  
  cat("Data grabbing completed successfully.\n")
}
