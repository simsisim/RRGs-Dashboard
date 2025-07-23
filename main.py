import streamlit as st
from datetime import date
from relative_rotation import RelativeRotationData, SPDRS

def main():
    st.set_page_config(page_title="RRG Dashboard", layout="wide")
    st.sidebar.title("RRG Parameters")

    # Data Source & Calculation Method
    data_source = st.sidebar.selectbox(
        "Select Data Source",
        ["Yahoo Finance", "Local Folder"],
        index=0
    )

    calculation_method = st.sidebar.selectbox(
        "Select Calculation Method",
        ["RRG: Momentum", "RRG: Moving Averages"],
        index=0
    )

    # Benchmark Selection
    benchmark = st.sidebar.selectbox(
        "Select Benchmark", ["SPY", "QQQ", "DIA", 'GLD', 'COPX'], index=0
    )

    # Parameter Controls
    if calculation_method == "RRG: Momentum":
        st.sidebar.header("Daily Parameters")
        window = st.sidebar.slider("Window Size - 1d", 10, 50, 20, 1)
        tail_length = st.sidebar.slider("Tail Length - 1d", 1, 12, 5, 1)
        st.sidebar.header("Weekly Parameters")
        window_1wk = st.sidebar.slider("Window Size - 1wk", 5, 20, 10, 1)
        tail_length_1wk = st.sidebar.slider("Tail Length - 1wk", 1, 20, 5, 1)
    else:
        ma_short = st.sidebar.slider("Short MA", 5, 55, 20, 5)
        ma_long = st.sidebar.slider("Long MA", 20, 205, 50, 5)
        tail_length = st.sidebar.slider("Tail Length", 1, 30, 6, 1)
        benchmark = None # Not used for MA method

    st.title("Relative Rotation Graph Dashboard")

    stocks = st.text_input(
        "Enter stocks (up to 20, comma-separated):",
        placeholder="e.g., XLB, XLC, XLE",
        max_chars=1000
    )

    if stocks:
        stock_list = [s.strip() for s in stocks.split(",") if s.strip()]
        if len(stock_list) > 20:
            st.error("Maximum 20 stocks allowed")
            return

        st.write(f"**Selected Stocks:** {', '.join(stock_list)}")
        st.write(f"**Method:** {calculation_method}")
        if calculation_method == "RRG: Momentum":
            st.write(f"**Benchmark:** {benchmark}")
            st.write(f"**Window:** {window}, **Tail Length:** {tail_length}")
        else:
            st.write(f"**Short MA:** {ma_short}, **Long MA:** {ma_long}, **Tail Length:** {tail_length}")

        target_date = date.today()
        chart_type = "rrg" if calculation_method == "RRG: Momentum" else "moving_average"
        local_folder_path = "/home/imagda/_invest2024/python/downloadData_v1/data/market_data"

        # Create RRG objects
        rrg_obj_daily_1 = RelativeRotationData(
            symbols=stock_list,
            benchmark=benchmark if calculation_method == "RRG: Momentum" else "N/A",
            study="price",
            date=target_date,
            window=window if calculation_method == "RRG: Momentum" else None,
            ma_short=ma_short if calculation_method == "RRG: Moving Averages" else None,
            ma_long=ma_long if calculation_method == "RRG: Moving Averages" else None,
            tail_length=tail_length,
            chart_type=chart_type,
            data_source=data_source,
            local_data_path=(local_folder_path if data_source == "Local Folder" else None),
            frequency="daily"
        )

        rrg_obj_weekly = RelativeRotationData(
            symbols=stock_list,
            benchmark=benchmark if calculation_method == "RRG: Momentum" else "N/A",
            study="price",
            date=target_date,
            window=window_1wk if calculation_method == "RRG: Momentum" else None,
            ma_short=ma_short if calculation_method == "RRG: Moving Averages" else None,
            ma_long=ma_long if calculation_method == "RRG: Moving Averages" else None,
            tail_length=tail_length_1wk if calculation_method == "RRG: Momentum" else tail_length,
            chart_type=chart_type,
            data_source=data_source,
            local_data_path=(local_folder_path if data_source == "Local Folder" else None),
            frequency="weekly"
        )

        # Load full data (do not filter yet)
        rrg_obj_daily_1.get_data()
        rrg_obj_weekly.get_data()

        # Sidebar date range controls (after loading data)
        full_index = rrg_obj_daily_1.symbols_data.index
        min_date = full_index.min().date()
        max_date = full_index.max().date()
        st.sidebar.header("Chart Date Range")
        start_range = st.sidebar.date_input("From", min_value=min_date, max_value=max_date, value=min_date)
        end_range = st.sidebar.date_input("To", min_value=min_date, max_value=max_date, value=max_date)
        if start_range > end_range:
            st.sidebar.error("Start date must be before end date.")
            return

        # Filter both objects to range
        for obj in [rrg_obj_daily_1, rrg_obj_weekly]:
            obj.symbols_data = obj.symbols_data.loc[start_range:end_range]
            obj.benchmark_data = obj.benchmark_data.loc[start_range:end_range]

        # Find common available date range for the time slider
        dates_daily = rrg_obj_daily_1.symbols_data.index
        dates_weekly = rrg_obj_weekly.symbols_data.index
        common_index = dates_daily.intersection(dates_weekly)
        if len(common_index) == 0:
            st.error("No overlapping dates in daily and weekly data! Check your symbols or source.")
            return



        # Optional: preview chart for benchmark’s price
        if benchmark and benchmark in rrg_obj_daily_1.benchmark_data.columns:
            st.line_chart(rrg_obj_daily_1.benchmark_data[benchmark].loc[common_index])



        # Allow user to show/hide tickers
        selected_symbols = st.multiselect(
            "Select tickers to show on the charts:",
            options=stock_list,
            default=stock_list
        )

        default_date = common_index[-1]
        selected_date = st.slider(
            "📅 Select Date (affects both charts):",
            min_value=common_index[0].date(),
            max_value=common_index[-1].date(),
            value=default_date.date(),
            format="YYYY-MM-DD"
        )
        # Filter up to the selected date
        for obj in [rrg_obj_daily_1, rrg_obj_weekly]:
            obj.symbols_data = obj.symbols_data.loc[:selected_date]
            obj.benchmark_data = obj.benchmark_data.loc[:selected_date]
            
        rrg_obj_daily_1.symbols = selected_symbols
        rrg_obj_daily_1.process_rotation_data()
        fig_daily_filtered = rrg_obj_daily_1.create_rrg_plot()

        rrg_obj_weekly.symbols = selected_symbols
        rrg_obj_weekly.process_rotation_data()
        fig_weekly_filtered = rrg_obj_weekly.create_rrg_plot()

        st.subheader("Daily RRG Chart")
        st.plotly_chart(fig_daily_filtered, use_container_width=True, key="daily_rrg_chart_1")

        st.subheader("Weekly RRG Chart")
        st.plotly_chart(fig_weekly_filtered, use_container_width=True, key="weekly_rrg_chart")

if __name__ == "__main__":
    main()
