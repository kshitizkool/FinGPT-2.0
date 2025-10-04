import streamlit as st
import plotly.graph_objects as go

def render_stock_charts(price_data: dict):
    """Render stock price charts"""
    for symbol, data in price_data.items():
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data['Date'],
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name=symbol
        ))
        fig.update_layout(
            title=f"{symbol} Stock Price",
            yaxis_title="Price ($)",
            xaxis_title="Date",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)