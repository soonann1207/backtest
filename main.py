import pandas as pd
import yfinance as yf

from backtest_engine import BacktestEngine

# Read Trade Order Data
trade_orders = pd.read_csv("data_store/order_input/aapl_demo_trade_order.csv")

# Convert the 'order_date' column to datetime
trade_orders["date"] = pd.to_datetime(trade_orders["date"], format="%Y-%m-%d")

# Read OHLC Data
SYMBOL = "AAPL"

# Download data from Yahoo Finance
ohlcv = yf.download(SYMBOL, start="2022-01-01", end="2024-06-01")
ohlcv.reset_index(inplace=True)

backtest_engine = BacktestEngine(
    trade_orders=trade_orders,
    ohlvc=ohlcv[["Date", "Open", "High", "Low", "Close"]],
    commission=0.02,
    # slippage=0.0,
    initial_capital=100000.0,
)

backtest_engine.backtest()
order_records = backtest_engine.order_records
stocks = backtest_engine.stocks
aapl_stock_entity = stocks["AAPL"]
trades_df = aapl_stock_entity.get_trades()
historical_records = aapl_stock_entity.get_historical_records()
