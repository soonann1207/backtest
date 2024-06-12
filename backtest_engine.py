import pandas as pd
from tqdm import tqdm

import constants
from entity import StockEntity

"""
class for Backtest Engine which takes in a trade order with the following details: 
Columns = ['stock', 'date', 'quantity', 'price', 'signal_type', 'order_type',
           'stop_loss', 'take_profit', 'trailing_stop', 'duration']

Example:
stock = 'AAPL'
date = '2020-01-01'
quantity = 100
price = 100
signal_type = 'buy'
order_type = 'market'
stop_loss = 0.02
take_profit = 0.02
trailing_stop = 0.02
duration = Day/Good Till Cancelled (GTC)/ Pre Market/ Post Market
"""

# TODO: add trigger: stop loss, take profit, trailing stop


class BacktestEngine:
    def __init__(
        self,
        trade_orders: pd.DataFrame,
        ohlvc: pd.DataFrame,
        commission: float = 0.02,
        # slippage=0.0: float,
        initial_capital: float = 100000.0,
    ):
        self.trade_orders = trade_orders
        self.stocks = {}  # Dictionary to store the stock entities
        self.ohlvc = ohlvc
        self.commission = commission
        # self.slippage = slippage
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.order_records = pd.DataFrame(
            data=[],
            columns=[
                "date",
                "stock",
                "quantity",
                "position_type",
                "price",
                "fees",
                "stop_loss",
                "take_profit",
                "trailing_stop",
                "order_status",
                "comments",
            ],
        )

        """
        Trade Records to track all the BUY & SELL transactions
        Date: Date of the transaction
        Stock: Stock symbol
        Quantity: Number of shares bought/sold
        Price: Price at which the transaction was made
        Fee: Commission charged for the transaction
        Status: Filled/Cancelled
        """

        """
        Trade Positions to track the current positions of the stock
        Date: Date of the transaction
        Stock: Stock symbol
        Quantity: Number of shares bought/sold
        Average Price: Average price of the stock
        Current Value: Current value of the stock
        Close Price: Close price of the stock
        Stop Loss: Stop loss for the stock
        Take Profit: Take profit for the stock
        Trailing Stop: Trailing stop for the stock
        
        Possible Params:
        Position Type: Long/Short
        Entry Timestamp
        Average Entry Price
        Entry Size
        Exit Timestamp
        Average Exit Price
        Exit Size
        Unrealized PnL
        Realized PnL
        Order Status: Open/Closed
        """

    def update_order_records(
        self,
        date,
        stock,
        quantity,
        position_type,
        price,
        fees,
        # order_type,
        stop_loss,
        take_profit,
        trailing_stop,
        order_status,
        comments="",
        # duration,
    ):
        new_trade_record = pd.DataFrame(
            {
                "date": date,
                "stock": stock,
                "quantity": quantity,
                "position_type": position_type,
                "price": price,
                "fees": fees,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "trailing_stop": trailing_stop,
                "order_status": order_status,
                "comments": comments,
                # "order_type": order_type,
                # "duration": duration,
            },
            index=[0],
        )
        self.order_records = pd.concat(
            [self.order_records, new_trade_record], ignore_index=True
        )

    def execute_trade(
        self,
        ticker,
        stock_entity,
        date,
        position_type,
        quantity,
        price,
        stop_loss,
        take_profit,
        trailing_stop,
        close_price,
        high_price,
        low_price,
    ):
        # Check type of trade
        if position_type == constants.LONG_POSITION:
            # Check if existing capital is enough to buy the stock with the given commission
            if self.current_capital < (quantity * price) + self.commission * (
                quantity * price
            ):
                print("Insufficient Capital")
                # Update DataFrame with the trade details
                self.update_order_records(
                    date=date,
                    stock=ticker,
                    quantity=quantity,
                    position_type=constants.LONG_POSITION,
                    price=price,
                    fees=self.commission * (quantity * price),
                    # order_type="Market",
                    order_status=constants.ORDER_STATUS_CANCELLED,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    comments="Insufficient Capital",
                    # duration=duration,
                )
                return

            # Check if the price is higher than low price
            if price < low_price:
                print("Bid price is lower than low price")
                self.update_order_records(
                    date=date,
                    stock=ticker,
                    quantity=quantity,
                    position_type=constants.LONG_POSITION,
                    price=price,
                    fees=self.commission * (quantity * price),
                    # order_type="Market",
                    order_status=constants.ORDER_STATUS_CANCELLED,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    comments="Bid price is lower than low price",
                    # duration=duration,
                )
                return

            # Execute the trade
            self.current_capital -= (quantity * price) + self.commission * (
                quantity * price
            )
            self.update_order_records(
                date=date,
                stock=ticker,
                quantity=quantity,
                position_type=constants.LONG_POSITION,
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                order_status=constants.ORDER_STATUS_FILLED,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )

            print("Trade Executed")
            stock_entity.buy(
                entry_date=date,
                position_type=position_type,
                price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                trade_status=constants.TRADE_STATUS_OPEN,
            )
            return

        elif position_type == constants.SHORT_POSITION:
            # Check if existing capital is enough to sell the stock with the given commission
            if self.current_capital < self.commission * (
                quantity * price
            ):  # TODO: check
                print("Insufficient Capital")
                self.update_order_records(
                    date=date,
                    stock=ticker,
                    quantity=quantity,
                    position_type=constants.SHORT_POSITION,
                    price=price,
                    fees=self.commission * (quantity * price),
                    # order_type="Market",
                    order_status=constants.ORDER_STATUS_CANCELLED,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    comments="Insufficient Capital",
                    # duration=duration,
                )
                return

            # Check if the price is lower than high price
            if price > high_price:
                print("Ask price is higher than high price")
                self.update_order_records(
                    date=date,
                    stock=ticker,
                    quantity=quantity,
                    position_type=constants.SHORT_POSITION,
                    price=price,
                    fees=self.commission * (quantity * price),
                    # order_type="Market",
                    order_status=constants.ORDER_STATUS_CANCELLED,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_stop=trailing_stop,
                    comments="Ask price is higher than high price",
                    # duration=duration,
                )
                return

            # Execute the trade
            self.current_capital += (quantity * price) - self.commission * (
                quantity * price
            )
            self.update_order_records(
                date=date,
                stock=ticker,
                quantity=quantity,
                position_type=constants.SHORT_POSITION,
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                order_status=constants.ORDER_STATUS_FILLED,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )
            print("Trade Executed")
            stock_entity.sell(
                entry_date=date,
                position_type=position_type,
                price=price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                trade_status=constants.TRADE_STATUS_OPEN,
            )

            return

        return

    def backtest(self):
        """
        Backtest the trade order
        Logic:
            1. Loop through each day in the price data [O]
            2. Check if any existing trades has hit the stop loss, take profit or trailing stop []
            3. Check if there are any new trades to be executed [O]
        """
        # Create StockEntity for each stock and store in the stocks dictionary
        for stock in self.trade_orders["stock"].unique():
            self.stocks[stock] = StockEntity(symbol=stock, commission=self.commission)

        order_records_dict = {}

        for _, row in self.trade_orders.iterrows():
            if row["stock"] not in order_records_dict:
                order_records_dict[row["stock"]] = []
            order_records_dict[row["stock"]].append(row["date"])

        for price_index, row in tqdm(self.ohlvc.iterrows(), total=len(self.ohlvc)):
            for ticker, stock_entity in self.stocks.items():
                stock_entity.stop_loss(row["Date"], row["High"], row["Low"])
                stock_entity.take_profit(row["Date"], row["High"], row["Low"])
                # check stop loss, take profit, trailing stop
                # print(stockEntity.trades)
                if row["Date"] in order_records_dict[ticker]:
                    trade_details = self.trade_orders.loc[
                        self.trade_orders["date"] == row["Date"]
                    ].squeeze()
                    stock = trade_details["stock"]
                    date = trade_details["date"]
                    position_type = trade_details["position_type"]
                    quantity = trade_details["quantity"]
                    price = trade_details["price"]
                    stop_loss = trade_details["stop_loss"]
                    take_profit = trade_details["take_profit"]
                    trailing_stop = trade_details["trailing_stop"]
                    # duration = trade_details["duration"]
                    # order_type = trade_details["order_type"]
                    self.execute_trade(
                        ticker=stock,
                        stock_entity=stock_entity,
                        date=date,
                        position_type=position_type,
                        quantity=quantity,
                        price=price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        trailing_stop=trailing_stop,
                        close_price=self.ohlvc["Close"].loc[price_index],
                        high_price=self.ohlvc["High"].loc[price_index],
                        low_price=self.ohlvc["Low"].loc[price_index],
                    )

                stock_entity.update_historical_records(
                    date=row["Date"], adjusted_close=row["Close"]
                )
