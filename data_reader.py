import pandas as pd
import os

class DataReader:
    def __init__(self, paths, combined_file):
        self.source_market_data = paths['source_market_data']
        self.dest_tickers_data = paths['dest_tickers_data']
        self.combined_file = combined_file 
    def read_tickers(self):
        return pd.read_csv(self.combined_file)['ticker'].tolist()

    def read_stock_data(self, ticker):
        file_path = os.path.join(self.source_market_data, f"{ticker}.csv")
        #df = pd.read_csv(file_path, header=0, parse_dates=['Date'], index_col='Date', date_parser=lambda x: pd.to_datetime(x.rpartition('-')[0]))
        df = pd.read_csv(file_path, index_col= 'Date', parse_dates=False)
        df.index = df.index.str.split(' ').str[0]
        df.index = pd.to_datetime(df.index)
        return df[['Close']]
    


    def create_combined_df(self):
        combined_df = pd.DataFrame()
        tickers = self.read_tickers()
        for ticker in tickers:
            df = self.read_stock_data(ticker)
            if df['Close'].isnull().any():
                print(f"Skipping ticker {ticker} due to missing data.")
                continue
            if len(df) < 252:  # Assuming 252 trading days in a year
                print(f"Skipping ticker {ticker} due to insufficient historical data.")
                continue
            
            df = df.rename(columns={'Close': ticker})
            #        # Debugging prints
            #print(f"Ticker: {ticker}")
            #print(f"Number of rows: {len(df)}")
            #print(f"Date range: {df.index.min()} to {df.index.max()}")
            #print(f"Number of duplicate indices: {df.index.duplicated().sum()}")
            #print(df.index.duplicated())
            #print(f"First few rows:\n{df.head()}\n")
            if ticker != '^BUK100P' and ticker != '^FTSE' and ticker != '^GDAXI' and ticker != '^FCHI' and ticker != '^STOXX50E' and ticker != '^N100' and ticker != '^BFX' and ticker != '^HSI' and ticker != '^STI':
                combined_df = pd.concat([combined_df, df], axis=1)
    
        return combined_df
