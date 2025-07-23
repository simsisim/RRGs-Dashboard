import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Literal, Optional, Tuple
from datetime import datetime, timedelta, date as dateType
from plotly import graph_objects as go
from warnings import warn
import plotly.graph_objects as go
import plotly.express as px  # For vibrant color palettes
from itertools import cycle  # For cycling through colors
from data_reader import DataReader
import os
SPDRS = [
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", 
    "XHB", "XLU", "XLV", "XLY", "XLRE"
]

import pandas as pd
import numpy as np



from data_reader import DataReader

class RelativeRotationData:
    def __init__(
        self,
        symbols: List[str],
        benchmark: str,
        tail_length: int,
        study: Literal["price", "volume", "volatility"] = "price",
        date: Optional[dateType] = None,
        window: Optional[int] = 50,
        ma_short: Optional[int] = None,  # Short MA window size
        ma_long: Optional[int] = None,  # Long MA window size
        chart_type: Literal["rrg", "moving_average"] = "rrg",
        data_source: Literal["Yahoo Finance", "Local Folder"] = "Yahoo Finance",
        local_data_path: Optional[str] = None
    ):
        self.symbols = symbols
        self.benchmark = benchmark
        self.study = study
        self.date = date
        self.window = window
        self.chart_type = chart_type
        self.tail_length = tail_length
        self.data_source = data_source
        self.local_data_path = local_data_path
        self.ma_short = ma_short  # Short MA window size
        self.ma_long = ma_long  # Long MA window size

        # Initialize other attributes
        self.start_date = None
        self.end_date = None
        self.symbols_data = None
        self.benchmark_data = None

    def get_data(self):
        """Fetch the data using the selected data source."""
        if self.data_source == "Yahoo Finance":
            # Fetch data from Yahoo Finance (existing logic)
            if self.date is None:
                end_date = datetime.now()
            else:
                end_date = self.date
    
            #if self.tail_interval == "week":
            #    start_date = end_date - timedelta(3 * 90)  # Approx. last quarter's data
            #else:
            start_date = end_date - timedelta(5 * 90)
    
            tickers = self.symbols + ([self.benchmark] if self.benchmark else [])
            data = yf.download(tickers, start=start_date, end=end_date)
    
            if self.study == "price":
                target_data = data["Close"]
            elif self.study == "volume":
                target_data = data["Volume"]
            #else:  # volatility study
            #    continue
            #    target_data = data["Close"].pct_change().rolling(window=21).std() * (252 ** 0.5)
    
            self.symbols_data = target_data[self.symbols]
            if self.benchmark:
                self.benchmark_data = target_data[[self.benchmark]]
    
            print(f"Data fetched for {len(self.symbols)} symbols and benchmark {self.benchmark}")
            print(f"Date range: {start_date} to {end_date}")
    
        elif self.data_source == "Local Folder":
            # Fetch data from local folder using DataReader class
            if not self.local_data_path:
                raise ValueError("Local data path must be provided for 'Local Folder' option.")
    
            reader_paths = {
                'source_market_data': self.local_data_path,
                'dest_tickers_data': "",  # Not used in this context
            }
    
            reader = DataReader(paths=reader_paths, combined_file=None)  # No need for combined_file
    
            combined_df = pd.DataFrame()
            for symbol in self.symbols:
                try:
                    df_symbol = reader.read_stock_data(symbol)
                    df_symbol.rename(columns={"Close": symbol}, inplace=True)
                    combined_df[symbol] = df_symbol[symbol]
                except FileNotFoundError as e:
                    print(f"Failed to get ticker '{symbol}' reason: {e}")
                    continue
    
            if self.benchmark and self.benchmark != "N/A":
                try:
                    df_benchmark = reader.read_stock_data(self.benchmark)
                    df_benchmark.rename(columns={"Close": self.benchmark}, inplace=True)
                    combined_df[self.benchmark] = df_benchmark[self.benchmark]
                except FileNotFoundError as e:
                    print(f"Failed to get benchmark '{self.benchmark}' reason: {e}")
                    raise ValueError(f"Benchmark file not found: {self.benchmark}")
    
            # Assign to class attributes
            self.symbols_data = combined_df[self.symbols]
            if self.benchmark and self.benchmark != "N/A":
                self.benchmark_data = combined_df[[self.benchmark]]
    
            print(f"Data fetched from local folder for {symbol} symbols.")

    def calculate_rrg_components(self, stock_prices, benchmark_prices, window=21):
        # Ensure we're working with the correct data types
        if isinstance(benchmark_prices, RelativeRotationData):
            benchmark_prices = benchmark_prices.benchmark_data[benchmark_prices.benchmark]
        
        # Align the data
        stock_prices, benchmark_prices = stock_prices.align(benchmark_prices, join='inner')
        
        # Calculate Relative Strength (RS)
        rs = (stock_prices / benchmark_prices) * 100
        
        # Calculate RS-Ratio
        rs_ratio = 100 + (rs - rs.rolling(window=window).mean()) / rs.rolling(window=window).std(ddof=0)
        rs_ratio = rs_ratio.dropna()
        
        # Calculate RS-Momentum
        rs_roc = 100 * (rs / rs.shift(1) - 1)
        rs_momentum = 100 + (rs_roc - rs_roc.rolling(window=window).mean()) / rs_roc.rolling(window=window).std(ddof=0)
        rs_momentum = rs_momentum.dropna()
        
        # Align indices
        rs_ratio = rs_ratio[rs_ratio.index.isin(rs_momentum.index)]
        rs_momentum = rs_momentum[rs_momentum.index.isin(rs_ratio.index)]
        
        return rs_ratio, rs_momentum
    
    def process_rrg_data(self):
        rrg_data = pd.DataFrame()
        for symbol in self.symbols:
            if symbol != self.benchmark:
                rs_ratio, rs_momentum = self.calculate_rrg_components(
                    self.symbols_data[symbol],
                    self.benchmark_data[self.benchmark],
                    window=self.window
                )
                rrg_data[f'{symbol}_RS_Ratio'] = rs_ratio
                rrg_data[f'{symbol}_RS_Momentum'] = rs_momentum
        self.rrg_data = rrg_data

    def process_rotation_data(self):
        if self.chart_type == "rrg":
            self.process_rrg_data()
        elif self.chart_type == "moving_average":
            self.process_moving_average_data()
    
    def process_moving_average_data(self):
        rrg_data = pd.DataFrame()
        for symbol in self.symbols:
            if symbol != self.benchmark:
                # Use user-defined windows for ShortMA and LongMA
                short_ma_window = self.ma_short if self.ma_short else 20  # Default to 20 if not provided
                long_ma_window = self.ma_long if self.ma_long else 50  # Default to 50 if not provided
    
                short_ma = self.symbols_data[symbol].rolling(window=short_ma_window).mean()
                long_ma = self.symbols_data[symbol].rolling(window=long_ma_window).mean()
                rrg_data[f'{symbol}_ShortMA'] = (self.symbols_data[symbol] - short_ma) / short_ma * 100
                rrg_data[f'{symbol}_LongMA'] = (self.symbols_data[symbol] - long_ma) / long_ma * 100
        self.rrg_data = rrg_data



    def create_rrg_plot(self):
        """Create RRG plot with quadrant coloring for Momentum and Moving Averages."""
        fig = go.Figure()
    
        if self.chart_type == "rrg":  # RRG: Momentum
            latest_dates = self.rrg_data.index[-self.tail_length:]
            latest_data = self.rrg_data.loc[latest_dates]
    
            # Define quadrant colors
            quadrant_colors = ['rgba(0, 128, 0, 0.4)',  # Leading (Green)
                               'rgba(255, 255, 0, 0.4)',  # Weakening (Yellow)
                               'rgba(255, 0, 0, 0.4)',  # Lagging (Red)
                               'rgba(0, 0, 255, 0.4)']  # Improving (Blue)
    
            # Add fixed quadrants
            fig.add_shape(type="rect", x0=100, y0=100, x1=105, y1=105,
                          fillcolor=quadrant_colors[0], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=95, y0=100, x1=100, y1=105,
                          fillcolor=quadrant_colors[3], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=95, y0=95, x1=100, y1=100,
                          fillcolor=quadrant_colors[2], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=100, y0=95, x1=105, y1=100,
                          fillcolor=quadrant_colors[1], line_color="Gray", opacity=0.6)
    
            # Add reference lines at x=100 and y=100
            fig.add_shape(type="line", x0=100, y0=95, x1=100, y1=105,
                          line=dict(color="Gray", width=1, dash="dot"))
            fig.add_shape(type="line", x0=95, y0=100, x1=105, y1=100,
                          line=dict(color="Gray", width=1, dash="dot"))
            
                       # Add quadrant labels
            fig.add_annotation(x=104.5, y=104.5, text="Leading", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=95.5, y=104.5, text="Improving", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=95.5, y=99.5, text="Lagging", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=104.5, y=99.5, text="Weakening", showarrow=False,
                               font=dict(size=14), align="center")
    
            # Add data points for each symbol
            colors = px.colors.qualitative.Dark24 * 5
            color_cycle = cycle(colors)
    
            for symbol in self.symbols:
                if symbol != self.benchmark:
                    color = next(color_cycle)
                    fig.add_trace(go.Scatter(
                        x=latest_data[f'{symbol}_RS_Ratio'],
                        y=latest_data[f'{symbol}_RS_Momentum'],
                        mode='lines+markers',
                        name=symbol,
                        line=dict(color=color),
                        marker=dict(size=[8] * (len(latest_dates) - 1) + [12])
                    ))
    
            # Set axis titles for RRG: Momentum
            x_axis_title = "RS-Ratio (Relative Strength Ratio)"
            y_axis_title = "RS-Momentum (Relative Strength Momentum)"

    
        elif self.chart_type == "moving_average":  # RRG: Moving Averages
            colors = px.colors.qualitative.Dark24 * 5
            color_cycle = cycle(colors)
        
            # Restrict data to the last tail_length points
            latest_dates = self.rrg_data.index[-self.tail_length:]
            latest_data = self.rrg_data.loc[latest_dates]
            
            # Calculate dynamic min/max values for X (LongMA) and Y (ShortMA)
            x_min = latest_data[[f'{symbol}_LongMA' for symbol in self.symbols]].min().min()#+5
            x_max = latest_data[[f'{symbol}_LongMA' for symbol in self.symbols]].max().max()#+5
            y_min = latest_data[[f'{symbol}_ShortMA' for symbol in self.symbols]].min().min()#+5
            y_max = latest_data[[f'{symbol}_ShortMA' for symbol in self.symbols]].max().max()#+5
        
            # Define quadrant colors
            # Define quadrant colors
            quadrant_colors = ['rgba(0, 128, 0, 0.4)',  # Leading (Green)
                               'rgba(255, 255, 0, 0.4)',  # Weakening (Yellow)
                               'rgba(255, 0, 0, 0.4)',  # Lagging (Red)
                               'rgba(0, 0, 255, 0.4)']  # Improving (Blue)
            # Add fixed quadrants
            fig.add_shape(type="rect", x0=0, y0=0, x1=45, y1=45,
                          fillcolor=quadrant_colors[0], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=-45, y0=0, x1=0, y1=45,
                          fillcolor=quadrant_colors[3], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=-45, y0=-45, x1=0, y1=0,
                          fillcolor=quadrant_colors[2], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=0, y0=-45, x1=45, y1=0,
                          fillcolor=quadrant_colors[1], line_color="Gray", opacity=0.6)
    
            # Add reference lines at x=100 and y=100
            fig.add_shape(type="line", x0=0, y0=-45, x1=0, y1=45,
                          line=dict(color="Gray", width=1, dash="dot"))
            fig.add_shape(type="line", x0=-45, y0=0, x1=45, y1=0,
                          line=dict(color="Gray", width=1, dash="dot"))
            
                       # Add quadrant labels
            fig.add_annotation(x=42.5, y=42.5, text="Leading", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=-42.5, y=42.5, text="Improving", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=-42.5, y=-1.8, text="Lagging", showarrow=False,
                               font=dict(size=14), align="center")
            fig.add_annotation(x=42.5, y=-1.8, text="Weakening", showarrow=False,
                               font=dict(size=14), align="center")


            
            for symbol in self.symbols:
                color = next(color_cycle)
        
                # ShortMA vs LongMA (solid line for ShortMA)
                fig.add_trace(go.Scatter(
                    x=latest_data[f'{symbol}_LongMA'],  # LongMA values on X-axis
                    y=latest_data[f'{symbol}_ShortMA'],  # ShortMA values on Y-axis
                    mode='lines+markers',
                    name=f"{symbol}  Percentage long MA vs short MA",
                    line=dict(color=color, width=2),  # Solid line for ShortMA
                    marker=dict(
                        size=[3] * (self.tail_length - 1) + [12],  # Larger marker for latest point
                        color=color,
                        opacity=[1] * (self.tail_length - 1) + [1],  # Latest point more opaque
                        symbol=['circle'] * (self.tail_length - 1) + ['diamond']
                    )
                ))
        
                # LongMA vs itself (optional dashed line for contrast)
                #fig.add_trace(go.Scatter(
                #    x=latest_data[f'{symbol}_LongMA'],  # LongMA values on X-axis
                #    y=latest_data[f'{symbol}_LongMA'],  # LongMA values on Y-axis (optional)
                #    mode='lines+markers',
                #    name=f"{symbol} Long MA",
                #    line=dict(color=color, width=2, dash='dash'),  # Dashed line for LongMA
                #    marker=dict(
                #        size=[3] * (self.tail_length - 1) + [12],
                #        color=color,
                #        opacity=[0.5] * (self.tail_length - 1) + [1],
                #        symbol=['circle'] * (self.tail_length - 1) + ['diamond']
                #    )
                #))
        
            # Set axis titles for RRG: Moving Averages
            x_axis_title = "Percentage Change Relative to long MA (%)"
            y_axis_title = "Percentage Change Relative to short MA (%)"
        
        # Update layout with dynamic axis titles
        fig.update_layout(
            title=f"Relative Rotation Graph ({self.chart_type.upper()})",
            xaxis_title=x_axis_title,
            yaxis_title=y_axis_title,
            template="plotly_white",
            height=800,
            width=800
        )
        
        return fig


