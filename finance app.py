# stock_market_visualizer.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import base64
import json
import io

# App Configuration
st.set_page_config(page_title="Stock Market Visualizer", layout="wide")
st.title("📈 Stock Market Visualizer")

# Session State Initialization
if 'config' not in st.session_state:
    st.session_state.config = {
        'timeframe': '1y',
        'colors': {'up': '#00ff00', 'down': '#ff0000'},
        'indicators': {'sma': False, 'ema': False, 'rsi': False, 'bollinger': False}
    }

# Sidebar
with st.sidebar:
    st.header("Settings")
    app_mode = st.selectbox("Navigation", ["Single Stock Analysis", "Portfolio Tracking", "Correlation Analysis"])
    
    # Configuration Saver
    st.subheader("Configuration Management")
    config_name = st.text_input("Save configuration as:")
    if st.button("Save Config"):
        with open(f"{config_name}.json", 'w') as f:
            json.dump(st.session_state.config, f)
        st.success(f"Saved as {config_name}.json")
    
    uploaded_config = st.file_uploader("Load Configuration", type=['json'])
    if uploaded_config:
        config_data = json.load(uploaded_config)
        st.session_state.config.update(config_data)
        st.success("Configuration loaded!")

# Single Stock Analysis
if app_mode == "Single Stock Analysis":
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Stock Analysis")
        ticker = st.text_input("Ticker Symbol", "AAPL")
        time_options = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        timeframe = st.selectbox("Timeframe", time_options, index=5)
        
        # Update config
        st.session_state.config['timeframe'] = timeframe
        
        st.subheader("Technical Indicators")
        sma = st.checkbox("SMA", value=st.session_state.config['indicators']['sma'])
        ema = st.checkbox("EMA", value=st.session_state.config['indicators']['ema'])
        rsi = st.checkbox("RSI", value=st.session_state.config['indicators']['rsi'])
        bollinger = st.checkbox("Bollinger Bands", value=st.session_state.config['indicators']['bollinger'])
        
        # Update indicators in config
        st.session_state.config['indicators'] = {
            'sma': sma,
            'ema': ema,
            'rsi': rsi,
            'bollinger': bollinger
        }
        
        # Customization
        st.subheader("Chart Customization")
        up_color = st.color_picker("Up Color", st.session_state.config['colors']['up'])
        down_color = st.color_picker("Down Color", st.session_state.config['colors']['down'])
        st.session_state.config['colors'] = {'up': up_color, 'down': down_color}
    
    # Fetch data
    @st.cache_data
    def load_data(ticker, period):
        return yf.Ticker(ticker).history(period=period)
    
    try:
        df = load_data(ticker, timeframe)
        if df.empty:
            st.error("No data found for this ticker/timeframe")
            st.stop()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()
    
    # Create chart
    fig = make_subplots(
        rows=3 if rsi else 2, 
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2] + ([0.2] if rsi else [])
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Price",
        increasing_line_color=up_color,
        decreasing_line_color=down_color
    ), row=1, col=1)
    
    # Technical Indicators
    if sma:
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA_50'], name="SMA 50", line=dict(color='blue', width=2)
        ), row=1, col=1)
    
    if ema:
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['EMA_20'], name="EMA 20", line=dict(color='orange', width=2)
        ), row=1, col=1)
    
    if bollinger:
        df['Middle'] = df['Close'].rolling(window=20).mean()
        df['Upper'] = df['Middle'] + 2 * df['Close'].rolling(window=20).std()
        df['Lower'] = df['Middle'] - 2 * df['Close'].rolling(window=20).std()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Upper'], name="Upper Band", line=dict(color='gray', width=1)
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['Lower'], name="Lower Band", line=dict(color='gray', width=1),
            fill='tonexty', fillcolor='rgba(128,128,128,0.2)'
        ), row=1, col=1)
    
    # Volume
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'], name="Volume", marker_color='#1f77b4'
    ), row=2, col=1)
    
    # RSI
    if rsi:
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        fig.add_trace(go.Scatter(
            x=df.index, y=df['RSI'], name="RSI", line=dict(color='purple', width=2)
        ), row=3, col=1)
        fig.add_hline(y=30, row=3, col=1, line_dash="dash", line_color="green")
        fig.add_hline(y=70, row=3, col=1, line_dash="dash", line_color="red")
    
    # Layout updates
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_dark"
    )
    
    with col2:
        st.plotly_chart(fig, use_container_width=True)
        
        # Export buttons
        col_export1, col_export2 = st.columns(2)
        with col_export1:
            buf = io.BytesIO()
            fig.write_image(file=buf, format="png")
            st.download_button(
                label="Download as PNG",
                data=buf,
                file_name=f"{ticker}_chart.png",
                mime="image/png"
            )
        with col_export2:
            html_buf = io.BytesIO()
            fig.write_html(html_buf)
            st.download_button(
                label="Download as HTML",
                data=html_buf.getvalue(),
                file_name=f"{ticker}_chart.html",
                mime="text/html"
            )

# Portfolio Tracking
elif app_mode == "Portfolio Tracking":
    st.subheader("Portfolio Analysis")
    
    uploaded_file = st.file_uploader("Upload Portfolio (CSV/Excel)", type=['csv', 'xlsx'])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                portfolio = pd.read_csv(uploaded_file)
            else:
                portfolio = pd.read_excel(uploaded_file)
            
            st.write("Portfolio Data:")
            st.dataframe(portfolio)
            
            # Validate columns
            required_cols = ['Ticker', 'Shares', 'Purchase_Price']
            if not all(col in portfolio.columns for col in required_cols):
                st.error("Missing required columns: Ticker, Shares, Purchase_Price")
                st.stop()
            
            # Fetch current prices
            portfolio['Current_Price'] = portfolio['Ticker'].apply(
                lambda x: yf.Ticker(x).history(period='1d')['Close'].iloc[-1]
            )
            portfolio['Current_Value'] = portfolio['Shares'] * portfolio['Current_Price']
            portfolio['Profit_Loss'] = portfolio['Current_Value'] - (
                portfolio['Shares'] * portfolio['Purchase_Price']
            )
            
            # Display results
            st.subheader("Portfolio Performance")
            st.dataframe(portfolio.style.format({
                'Current_Price': '${:.2f}',
                'Current_Value': '${:,.2f}',
                'Profit_Loss': '${:,.2f}'
            }))
            
            # Summary metrics
            total_investment = (portfolio['Shares'] * portfolio['Purchase_Price']).sum()
            total_current = portfolio['Current_Value'].sum()
            total_pl = total_current - total_investment
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Investment", f"${total_investment:,.2f}")
            col2.metric("Current Value", f"${total_current:,.2f}")
            col3.metric("Profit/Loss", f"${total_pl:,.2f}", f"{total_pl/total_investment*100:.2f}%")
            
        except Exception as e:
            st.error(f"Error processing portfolio: {e}")

# Correlation Analysis
elif app_mode == "Correlation Analysis":
    st.subheader("Stock Correlation Analysis")
    
    tickers = st.text_input("Enter stock tickers (comma separated)", "AAPL,MSFT,GOOG,AMZN")
    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    period = st.selectbox("Analysis Period", ['1mo','3mo','6mo','1y','2y','5y'], index=3)
    
    @st.cache_data
    def load_multiple_data(tickers, period):
        data = {}
        for t in tickers:
            try:
                df = yf.Ticker(t).history(period=period)
                data[t] = df['Close']
            except:
                st.warning(f"Could not load data for {t}")
        return pd.DataFrame(data)
    
    df = load_multiple_data(ticker_list, period)
    
    if not df.empty:
        st.subheader("Price Correlation Matrix")
        
        # Calculate correlations
        corr_matrix = df.corr()
        
        # Plot heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=ax)
        st.pyplot(fig)
        
        # Display correlation data
        st.write("Correlation Values:")
        st.dataframe(corr_matrix)
        
        # Time series visualization
        st.subheader("Normalized Price Comparison")
        normalized_df = df / df.iloc[0]
        fig = go.Figure()
        for col in normalized_df.columns:
            fig.add_trace(go.Scatter(
                x=normalized_df.index,
                y=normalized_df[col],
                name=col,
                mode='lines'
            ))
        fig.update_layout(
            title="Normalized Price Performance",
            yaxis_title="Normalized Price",
            hovermode="x unified",
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No valid data to analyze")

# How to Run section
st.sidebar.markdown("""
**How to Run:**
1. Install requirements: `pip install streamlit yfinance plotly pandas numpy seaborn matplotlib`
2. Run app: `streamlit run stock_market_visualizer.py`
""")
