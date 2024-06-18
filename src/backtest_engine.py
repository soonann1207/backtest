import pandas as pd
from tqdm import tqdm

from src import constants
from src.entity import StockEntity, Trade
from src.ibkr_fees import calculate_ibkr_fixed_cost

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
        self.fees = 0.0
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
        comments: str = "",
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
        if self.order_records.empty:
            self.order_records = new_trade_record
        else:
            self.order_records = pd.concat(
                [self.order_records, new_trade_record], ignore_index=True
            )
    @staticmethod
    def calculate_fees(price, quantity):
        return calculate_ibkr_fixed_cost(qty=quantity, price_per_share=price)

    @staticmethod
    def stop_loss_triggered(high_price, low_price, stop_loss, position_type):
        if position_type == constants.LONG_POSITION and low_price <= stop_loss:
            return True
        elif position_type == constants.SHORT_POSITION and high_price >= stop_loss:
            return True
        else:
            return False

    @staticmethod
    def take_profit_triggered(high_price, low_price, take_profit, position_type):
        if position_type == constants.LONG_POSITION and high_price >= take_profit:
            return True
        elif position_type == constants.SHORT_POSITION and low_price <= take_profit:
            return True
        else:
            return False

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

        for _, row in tqdm(self.ohlvc.iterrows(), total=len(self.ohlvc)):
            for ticker, stock_entity in self.stocks.items():
                # Check if stop_loss is triggered
                open_positions = stock_entity.get_open_position()
                for index, position in open_positions.iterrows():
                    if self.stop_loss_triggered(
                        row["High"],
                        row["Low"],
                        position["stop_loss"],
                        position["position_type"],
                    ):
                        fees = self.calculate_fees(row["High"], position["quantity"])
                        if position["position_type"] == constants.LONG_POSITION:
                            stock_entity.sell(
                                Trade(
                                    exit_date=row["Date"],
                                    exit_action=constants.TRADE_ACTION_SELL,
                                    exit_price=position["stop_loss"],
                                    quantity=position["quantity"],
                                    exit_fees=fees,
                                    trigger=constants.TRADE_TRIGGER_STOP_LOSS,
                                    trade_status=constants.TRADE_STATUS_CLOSED,
                                ),
                                open_position=index,
                            )
                            # Update capital and fees
                            self.current_capital += (
                                position["stop_loss"] * position["quantity"]
                            )
                            self.current_capital -= fees
                            self.fees += fees

                        else:
                            stock_entity.buy(
                                Trade(
                                    exit_date=row["Date"],
                                    exit_action=constants.TRADE_ACTION_BUY,
                                    exit_price=position["stop_loss"],
                                    quantity=position["quantity"],
                                    exit_fees=self.calculate_fees(
                                        row["Low"], position["quantity"]
                                    ),
                                    trigger=constants.TRADE_TRIGGER_STOP_LOSS,
                                    trade_status=constants.TRADE_STATUS_CLOSED,
                                ),
                                open_position=index,
                            )
                            # Update capital and fees
                            self.current_capital -= (
                                position["stop_loss"] * position["quantity"]
                            )
                            self.current_capital -= fees
                            self.fees += fees

                    if self.take_profit_triggered(
                        row["High"],
                        row["Low"],
                        position["take_profit"],
                        position["position_type"],
                    ):
                        fees = self.calculate_fees(row["High"], position["quantity"])
                        if position["position_type"] == constants.LONG_POSITION:
                            stock_entity.sell(
                                Trade(
                                    exit_date=row["Date"],
                                    exit_action=constants.TRADE_ACTION_SELL,
                                    exit_price=position["take_profit"],
                                    quantity=position["quantity"],
                                    exit_fees=self.calculate_fees(
                                        row["High"], position["quantity"]
                                    ),
                                    trigger=constants.TRADE_TRIGGER_TAKE_PROFIT,
                                    trade_status=constants.TRADE_STATUS_CLOSED,
                                ),
                                open_position=index,
                            )
                            # Update capital and fees
                            self.current_capital += (
                                position["take_profit"] * position["quantity"]
                            )
                            self.current_capital -= fees
                            self.fees += fees
                        else:
                            stock_entity.buy(
                                Trade(
                                    exit_date=row["Date"],
                                    exit_action=constants.TRADE_ACTION_BUY,
                                    exit_price=position["take_profit"],
                                    quantity=position["quantity"],
                                    exit_fees=self.calculate_fees(
                                        row["High"], position["quantity"]
                                    ),
                                    trigger=constants.TRADE_TRIGGER_TAKE_PROFIT,
                                    trade_status=constants.TRADE_STATUS_CLOSED,
                                ),
                                open_position=index,
                            )
                            # Update capital and fees
                            self.current_capital -= (
                                position["take_profit"] * position["quantity"]
                            )
                            self.current_capital -= fees
                            self.fees += fees

                # TODO: implement for trailing stop

                if row["Date"] in order_records_dict[ticker]:
                    trade_details = self.trade_orders.loc[
                        self.trade_orders["date"] == row["Date"]
                    ].squeeze()
                    date = trade_details["date"]
                    stock = trade_details["stock"]
                    quantity = trade_details["quantity"]
                    position_type = trade_details["position_type"]
                    price = trade_details["price"]
                    stop_loss = trade_details["stop_loss"]
                    take_profit = trade_details["take_profit"]
                    trailing_stop = trade_details["trailing_stop"]
                    order_status = ""
                    comments = ""

                    # Check if there is sufficient capital to execute the trade
                    fees = self.calculate_fees(price, quantity)
                    if self.current_capital < (quantity * price) + fees:
                        order_status = constants.ORDER_STATUS_CANCELLED
                        comments = "Insufficient Capital"
                    else:
                        if position_type == constants.LONG_POSITION:
                            if price < row["Low"]:
                                order_status = constants.ORDER_STATUS_CANCELLED
                                comments = "Bid price is lower than low price"
                            else:
                                # Update capital, fees

                                order_status = constants.ORDER_STATUS_FILLED
                                stock_entity.buy(
                                    Trade(
                                        entry_date=date,
                                        position_type=position_type,
                                        entry_action=constants.TRADE_ACTION_BUY,
                                        entry_price=price,
                                        quantity=quantity,
                                        entry_fees=fees,
                                        stop_loss=stop_loss,
                                        take_profit=take_profit,
                                        trailing_stop=trailing_stop,
                                        trade_status=constants.TRADE_STATUS_OPEN,
                                    )
                                )
                                self.current_capital -= quantity * price
                                self.current_capital -= fees
                                self.fees += fees
                        elif position_type == constants.SHORT_POSITION:
                            if price > row["High"]:
                                order_status = constants.ORDER_STATUS_CANCELLED
                                comments = "Ask price is higher than high price"
                            else:
                                # Update capital, fees

                                order_status = constants.ORDER_STATUS_FILLED
                                stock_entity.sell(
                                    Trade(
                                        entry_date=date,
                                        position_type=position_type,
                                        entry_action=constants.TRADE_ACTION_SELL,
                                        entry_price=price,
                                        quantity=quantity,
                                        entry_fees=fees,
                                        stop_loss=stop_loss,
                                        take_profit=take_profit,
                                        trailing_stop=trailing_stop,
                                        trade_status=constants.TRADE_STATUS_OPEN,
                                    )
                                )
                                self.current_capital += quantity * price
                                self.current_capital -= fees
                                self.fees += fees

                    self.update_order_records(
                        date=date,
                        stock=stock,
                        quantity=quantity,
                        position_type=position_type,
                        price=price,
                        fees=fees,
                        # order_type=order_type,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        trailing_stop=trailing_stop,
                        order_status=order_status,
                        comments=comments,
                        # duration=duration,
                    )

                stock_entity.update_historical_records(
                    date=row["Date"], adjusted_close=row["Close"]
                )
