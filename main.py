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
    if calculation_method == "RRG: Momentum":
        benchmark = st.sidebar.selectbox("Select Benchmark", ["SPY", "QQQ", "DIA", 'GLD', 'COPX'], index=0)
        window = st.sidebar.slider("Window Size", 10, 100, 51, 1)
        tail_length = st.sidebar.slider("Tail Length", 1, 12, 6, 1)
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
                st.write(f"**Window:** {window}, **Tail Length:** {tail_length}")
            else:
                st.write(f"**Short MA:** {ma_short}, **Long MA:** {ma_long}, **Tail Length:** {tail_length}")

            target_date = date(2025, 3, 27)
            chart_type = "rrg" if calculation_method == "RRG: Momentum" else "moving_average"
            
            local_folder_path = "/home/imagda/_invest2024/python/downloadData_v1/data/market_data"
            
            rrg_obj = RelativeRotationData(
                symbols=stock_list,
                benchmark=benchmark if calculation_method == "RRG: Momentum" else "N/A",
                study="price",
                date=target_date,
                window=window if calculation_method == "RRG: Momentum" else None,  # Window is used only for Momentum
                ma_short=ma_short if calculation_method == "RRG: Moving Averages" else None,  # Short MA window
                ma_long=ma_long if calculation_method == "RRG: Moving Averages" else None,  # Long MA window
                tail_length=tail_length,# if calculation_method == "RRG: Momentum" else ma_long,
                chart_type=chart_type,
                data_source=data_source,
                local_data_path=(local_folder_path if data_source == "Local Folder" else None),
            )

            rrg_obj.get_data()
            rrg_obj.process_rotation_data()
            print(rrg_obj.rrg_data)
            
            fig = rrg_obj.create_rrg_plot()
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
