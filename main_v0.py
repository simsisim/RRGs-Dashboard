import streamlit as st
from datetime import date
from relative_rotation import RelativeRotationData, SPDRS

def main():
    st.set_page_config(page_title="RRG Dashboard", layout="wide")

    # Sidebar Configuration
    st.sidebar.title("RRG Parameters")
    # Data Source Selection
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

    # Conditionally show benchmark only for Momentum method
    benchmark = st.sidebar.selectbox("Select Benchmark", ["SPY", "QQQ", "DIA", 'GLD', 'COPX'], index=0)
    if calculation_method == "RRG: Momentum":
        # Title for daily settings
        st.sidebar.header("Daily Parameters")
        window = st.sidebar.slider("Window Size - 1d", 10, 100, 51, 1)
        tail_length = st.sidebar.slider("Tail Length - 1d", 1, 12, 6, 1)
    
        # Title for weekly settings
        st.sidebar.header("Weekly Parameters")
        window_1wk = st.sidebar.slider("Window Size - 1wk", 10, 100, 51, 1)
        tail_length_1wk = st.sidebar.slider("Tail Length - 1wk", 1, 12, 6, 1)

    else:  # Moving Averages
        #window = st.sidebar.slider("MA Window Size", 5, 100, 51, 5)
        ma_short = st.sidebar.slider("Short MA", 5, 55, 20, 5)
        ma_long = st.sidebar.slider("Long MA", 20, 205, 50, 5)
        tail_length = st.sidebar.slider("Tail Length",1, 30, 6, 1)
        benchmark = None  # Not used for MA method

    # Main Page
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
        else:
            st.write(f"**Selected Stocks:** {', '.join(stock_list)}")
            st.write(f"**Method:** {calculation_method}")
            if calculation_method == "RRG: Momentum":
                st.write(f"**Benchmark:** {benchmark}")
    
                # DAILY RRG OBJECT
                rrg_obj_daily = RelativeRotationData(
                    symbols=stock_list,
                    benchmark=benchmark,
                    study="price",
                    date=target_date,
                    window=window,
                    tail_length=tail_length,
                    chart_type="rrg",
                    data_source=data_source,
                    local_data_path=(local_folder_path if data_source == "Local Folder" else None),
                )
                rrg_obj_daily.get_data()
                rrg_obj_daily.process_rotation_data()
                fig_daily = rrg_obj_daily.create_rrg_plot()
    
                # WEEKLY RRG OBJECT
                rrg_obj_weekly = RelativeRotationData(
                    symbols=stock_list,
                    benchmark=benchmark,
                    study="price",
                    date=target_date,
                    window=window_1wk,
                    tail_length=tail_length_1wk,
                    chart_type="rrg",
                    data_source=data_source,
                    local_data_path=(local_folder_path if data_source == "Local Folder" else None),
                )
                # For weekly, you must ensure your DataReader loads weekly data (see note below)
                rrg_obj_weekly.get_data()
                rrg_obj_weekly.process_rotation_data()
                fig_weekly = rrg_obj_weekly.create_rrg_plot()
    
                # DISPLAY BOTH CHARTS
                col1, col2 = st.columns(2)
                col1.subheader("Daily RRG")
                col1.plotly_chart(fig_daily, use_container_width=True)
                col2.subheader("Weekly RRG")
                col2.plotly_chart(fig_weekly, use_container_width=True)
    
            else:  # RRG: Moving Averages
                # ...current logic for the moving average chart...


if __name__ == "__main__":
    main()
