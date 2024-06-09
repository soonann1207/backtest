import pandas as pd
import yfinance as yf

from backtest_engine import BacktestEngine

# Read Trade Order Data
trade_order = pd.read_csv('data_store/order_input/aapl_demo_trade_order.csv')

# Convert the 'order_date' column to datetime
trade_order['date'] = pd.to_datetime(trade_order['date'], format='%Y-%m-%d')

# Read OHLC Data
symbol = 'AAPL'

# Download data from Yahoo Finance
ohlcv = yf.download(symbol, start='2022-01-01', end='2024-05-01')
ohlcv.reset_index(inplace=True)

backtest_engine = BacktestEngine(trade_order=trade_order,
                                 ohlc=ohlcv[['Date', 'Open', 'High', 'Low', 'Close']],
                                 commission=0.0,
                                 slippage=0.0,
                                 initial_capital=100000.0)

backtest_engine.backtest()
trade_records = backtest_engine.trade_records
trade_positions = backtest_engine.trade_positions