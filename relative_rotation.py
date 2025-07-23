import yfinance as yf

import pandas as pd

import numpy as np

from typing import List, Literal, Optional

from datetime import datetime, timedelta, date as dateType

from plotly import graph_objects as go

import plotly.express as px

from itertools import cycle

from data_reader import DataReader

SPDRS = [
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP",
    "XHB", "XLU", "XLV", "XLY", "XLRE"
]

class RelativeRotationData:
    def __init__(
        self,
        symbols: List[str],
        benchmark: str,
        tail_length: int,
        study: Literal["price", "volume", "volatility"] = "price",
        date: Optional[dateType] = None,
        window: Optional[int] = 20,
        ma_short: Optional[int] = None,
        ma_long: Optional[int] = None,
        chart_type: Literal["rrg", "moving_average"] = "rrg",
        data_source: Literal["Yahoo Finance", "Local Folder"] = "Yahoo Finance",
        local_data_path: Optional[str] = None,
        frequency: Literal["daily", "weekly"] = "daily"
    ):
        self.symbols = symbols
        self.benchmark = benchmark
        self.study = study
        self.date = date
        self.window = window
        self.tail_length = tail_length
        self.chart_type = chart_type
        self.data_source = data_source
        self.local_data_path = local_data_path
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.frequency = frequency
        self.start_date = None
        self.end_date = None
        self.symbols_data = None
        self.benchmark_data = None

    def wma(self, series, window):
        weights = np.arange(1, window + 1)
        return series.rolling(window).apply(lambda x: np.dot(x, weights)/weights.sum(), raw=True)

    def calculate_rrg_components_tradingview(self, stock_prices, benchmark_prices, window=20):
        stock_prices, benchmark_prices = stock_prices.align(benchmark_prices, join='inner')
        rs = stock_prices / benchmark_prices
        wma_rs = self.wma(rs, window)
        rs_ratio = self.wma(rs / wma_rs, window) * 100
        rs_mom = rs_ratio / self.wma(rs_ratio, window) * 100
        rs_ratio = rs_ratio.dropna()
        rs_mom = rs_mom.dropna()
        return rs_ratio, rs_mom

    def get_data(self):
        if self.data_source == "Yahoo Finance":
            end_date = self.date or datetime.now()
            start_date = end_date - timedelta(5 * 90)
            tickers = self.symbols + ([self.benchmark] if self.benchmark else [])
            interval = "1d" if self.frequency == "daily" else "1wk"
            data = yf.download(tickers, start=start_date, end=end_date, interval=interval)
            if self.study == "price":
                target_data = data["Close"]
            elif self.study == "volume":
                target_data = data["Volume"]
            self.symbols_data = target_data[self.symbols]
            if self.benchmark:
                self.benchmark_data = target_data[[self.benchmark]]

        elif self.data_source == "Local Folder":
            if not self.local_data_path:
                raise ValueError("Local data path must be provided for 'Local Folder'.")
            reader = DataReader({'source_market_data': self.local_data_path, 'dest_tickers_data': ""}, combined_file=None)
            combined_df = pd.DataFrame()
            for symbol in self.symbols:
                try:
                    df_symbol = reader.read_stock_data(symbol)
                    combined_df[symbol] = df_symbol["Close"].rename(symbol)
                except FileNotFoundError:
                    continue
            if self.benchmark:
                df_benchmark = reader.read_stock_data(self.benchmark)
                combined_df[self.benchmark] = df_benchmark["Close"]
            self.symbols_data = combined_df[self.symbols]
            self.benchmark_data = combined_df[[self.benchmark]]

    def calculate_rrg_components(self, stock_prices, benchmark_prices, window=21):
        stock_prices, benchmark_prices = stock_prices.align(benchmark_prices, join='inner')
        rs = (stock_prices / benchmark_prices) * 100
        rs_ratio = 100 + (rs - rs.rolling(window=window).mean()) / rs.rolling(window=window).std(ddof=0)
        rs_ratio = rs_ratio.dropna()
        rs_roc = 100 * (rs / rs.shift(1) - 1)
        rs_momentum = 100 + (rs_roc - rs_roc.rolling(window=window).mean()) / rs_roc.rolling(window=window).std(ddof=0)
        rs_momentum = rs_momentum.dropna()
        rs_ratio = rs_ratio[rs_ratio.index.isin(rs_momentum.index)]
        rs_momentum = rs_momentum[rs_momentum.index.isin(rs_ratio.index)]
        return rs_ratio, rs_momentum

    def process_rrg_data(self):
        rrg_data = pd.DataFrame()
        for symbol in self.symbols:
            if symbol != self.benchmark:
                #if self.frequency == "daily":
                rs_ratio, rs_momentum = self.calculate_rrg_components_tradingview(
                        self.symbols_data[symbol],
                        self.benchmark_data[self.benchmark],
                        window=self.window or 20
                )
                #else:
                #    rs_ratio, rs_momentum = self.calculate_rrg_components(
                #        self.symbols_data[symbol],
                #        self.benchmark_data[self.benchmark],
                #        window=self.window or 20
                #    )
                rrg_data[f'{symbol}_RS_Ratio'] = rs_ratio
                rrg_data[f'{symbol}_RS_Momentum'] = rs_momentum
        self.rrg_data = rrg_data

    def process_moving_average_data(self):
        rrg_data = pd.DataFrame()
        for symbol in self.symbols:
            if symbol != self.benchmark:
                short_ma_window = self.ma_short if self.ma_short else 20
                long_ma_window = self.ma_long if self.ma_long else 50
                short_ma = self.symbols_data[symbol].rolling(window=short_ma_window).mean()
                long_ma = self.symbols_data[symbol].rolling(window=long_ma_window).mean()
                rrg_data[f'{symbol}_ShortMA'] = (self.symbols_data[symbol] - short_ma) / short_ma * 100
                rrg_data[f'{symbol}_LongMA'] = (self.symbols_data[symbol] - long_ma) / long_ma * 100
        self.rrg_data = rrg_data

    def process_rotation_data(self):
        if self.chart_type == "rrg":
            self.process_rrg_data()
        elif self.chart_type == "moving_average":
            self.process_moving_average_data()

    def create_rrg_plot(self):
        fig = go.Figure()
        if self.chart_type == "rrg":  # RRG: Momentum
            latest_dates = self.rrg_data.index[-self.tail_length:]
            latest_data = self.rrg_data.loc[latest_dates]

            ratio_cols = [f'{symbol}_RS_Ratio' for symbol in self.symbols if symbol != self.benchmark]
            momentum_cols = [f'{symbol}_RS_Momentum' for symbol in self.symbols if symbol != self.benchmark]

            # --- FIXED AXES AND QUADRANTS (like StockCharts) ---
            x_range = [88, 112]
            y_range = [90, 112]
            fig.update_xaxes(range=x_range)
            fig.update_yaxes(range=y_range)

            center_x = 100
            center_y = 100
            x0, x1 = x_range
            y0, y1 = y_range

            quadrant_colors = [
                'rgba(0, 128, 0, 0.4)',     # Leading (Green)
                'rgba(255, 255, 0, 0.4)',   # Weakening (Yellow)
                'rgba(255, 0, 0, 0.4)',     # Lagging (Red)
                'rgba(0, 0, 255, 0.4)'      # Improving (Blue)
            ]
            # Draw quadrants with fixed boundaries
            fig.add_shape(type="rect", x0=center_x, y0=center_y, x1=x1, y1=y1, fillcolor=quadrant_colors[0], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=x0, y0=center_y, x1=center_x, y1=y1, fillcolor=quadrant_colors[3], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=x0, y0=y0, x1=center_x, y1=center_y, fillcolor=quadrant_colors[2], line_color="Gray", opacity=0.6)
            fig.add_shape(type="rect", x0=center_x, y0=y0, x1=x1, y1=center_y, fillcolor=quadrant_colors[1], line_color="Gray", opacity=0.6)

            fig.add_shape(type="line", x0=center_x, y0=y0, x1=center_x, y1=y1, line=dict(color="Gray", width=1, dash="dot"))
            fig.add_shape(type="line", x0=x0, y0=center_y, x1=x1, y1=center_y, line=dict(color="Gray", width=1, dash="dot"))

            fig.add_annotation(x=x1-2, y=y1-2, text="Leading", showarrow=False, font=dict(size=14), align="center")
            fig.add_annotation(x=x0+2, y=y1-2, text="Improving", showarrow=False, font=dict(size=14), align="center")
            fig.add_annotation(x=x0+2, y=y0+2, text="Lagging", showarrow=False, font=dict(size=14), align="center")
            fig.add_annotation(x=x1-2, y=y0+2, text="Weakening", showarrow=False, font=dict(size=14), align="center")

            # Plot the trails for each symbol
            # colors = cycle(px.colors.qualitative.Dark24)
            # for symbol in self.symbols:
            #     if symbol != self.benchmark:
            #         color = next(colors)
            #         xs = latest_data[f'{symbol}_RS_Ratio']
            #         ys = latest_data[f'{symbol}_RS_Momentum']
            #         fig.add_trace(go.Scatter(
            #             x=xs,
            #             y=ys,
            #             mode='lines+markers',
            #             name=symbol,
            #             line=dict(color=color),
            #             marker=dict(size=[8] * (len(xs) - 1) + [12], color=color, symbol="circle"),
            #             showlegend=True
            #         ))

            # fig.update_layout(
            #     title="Relative Rotation Graph (Momentum)",
            #     xaxis_title="RS-Ratio",
            #     yaxis_title="RS-Momentum",
            #     width=500, height=600,
            #     template="plotly_white"
            # )

        colors = cycle(px.colors.qualitative.Dark24)
        for symbol in self.symbols:
            if symbol != self.benchmark:
                color = next(colors)
                xs = latest_data[f'{symbol}_RS_Ratio']
                ys = latest_data[f'{symbol}_RS_Momentum']
        
                # Plot the trail line with thicker width
                fig.add_trace(go.Scatter(
                    x=xs,
                    y=ys,
                    mode='lines+markers',
                    name=symbol,
                    line=dict(color=color, width=3),  # Thicker line
                    marker=dict(
                        color=color,
                        size=8,
                        symbol="circle"
                    ),
                    showlegend=True
                ))
        
                # Draw arrow for the latest movement direction (between last two points)
                if len(xs) >= 2:
                    fig.add_annotation(
                        x=xs.iloc[-1],
                        y=ys.iloc[-1],
                        ax=xs.iloc[-2],
                        ay=ys.iloc[-2],
                        xref="x", yref="y",
                        axref="x", ayref="y",
                        showarrow=True,
                        arrowhead=3,
                        arrowwidth=2,
                        arrowsize=1.5,
                        arrowcolor=color,
                        opacity=1,
                        text=""
                    )
            fig.update_layout(
                title="Relative Rotation Graph (Momentum)",
                xaxis_title="RS-Ratio",
                yaxis_title="RS-Momentum",
                width=500, height=600,
                template="plotly_white"
            )

        # (If you have code for moving averages, you may similarly set fixed axes)
        return fig
