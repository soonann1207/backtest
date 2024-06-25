import typing
from dataclasses import dataclass
from datetime import datetime
from typing import List

import pandas as pd
from tqdm import tqdm

from src import constants
from src.entity import StockEntity, Trade
from src.ibkr_fees import calculate_ibkr_fixed_cost


@dataclass
class Order:
    order_id: int
    attached_order: bool
    ticker: str
    order_type: str
    action: str
    limit_price: float
    time_in_force: str
    quantity: float
    order_date: str = ""
    stop_price: float = 0.0
    trail_type: str = ""
    trail: float = 0.0

    @staticmethod
    def get_pandas_timestamp(date) -> pd.Timestamp:
        return pd.Timestamp(date)


class BacktestEngine:
    ORDER_BOOK_COLUMNS = [
        "order_date",
        "ticker",
        "order_type",
        "action",
        "price",
        "quantity",
        "trail_type",
        "trail",
        "time_in_force",
        "order_status",
        "comments",
        "filled_date",
    ]

    PORTFOLIO_RECORDS_COLUMNS = [
        "date",
        "stock",
        "adjusted_close",
        "long_position_quantity",
        "short_position_quantity",
        "stock_value",
        "total_fees",
        "existing_capital",
        "portfolio_value",
    ]

    PORTFOLIO_STATS_COLUMNS = [
        "date",
        "sharpe",
        "turnover",
        "returns",
        "max_drawdown",
        "margin",
        "long_count",
        "short_count",
    ]

    def __init__(
        self,
        order_book: pd.DataFrame,
        ohlvc: pd.DataFrame,
        # slippage=0.0: float,
        initial_capital: float = 100000.0,
    ):
        self.order_book = order_book.copy()
        self.stocks = {}  # Dictionary to store the stock entities
        self.ohlvc = ohlvc.copy()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.fees = 0.0
        self.portfolio_records = self._initialize_dataframe(self.PORTFOLIO_RECORDS_COLUMNS)
        self.portfolio_stats = self._initialize_dataframe(self.PORTFOLIO_STATS_COLUMNS)

        self.order_book["status"] = ""
        self.order_book["comments"] = ""
        self.order_book["filled_date"] = ""

    @staticmethod
    def _initialize_dataframe(columns: List[str]) -> pd.DataFrame:
        return pd.DataFrame(columns=columns)

    @staticmethod
    def calculate_fees(qty, price_per_share):
        return calculate_ibkr_fixed_cost(qty=qty, price_per_share=price_per_share)

    @staticmethod
    def stop_loss_trigger(stop_price, action, price) -> bool:
        """
        Check if the stop loss price is triggered

        If the action is BUY, then the price will be the HIGH price
        If the action is SELL, then the price will be the LOW price

        :param stop_price:
        :param action:
        :param price:
        :return:
        """
        if action == constants.TRADE_ACTION_BUY:
            return price >= stop_price
        elif action == constants.TRADE_ACTION_SELL:
            return price <= stop_price

    @staticmethod
    def update_trailing_stop_price(trail_type, trail, action, price) -> float:
        """
        Update the trailing stop price based on the trail type and trail value

        If the action is BUY, then the price will be the LOW price + trail
        If the action is SELL, then the price will be the HIGH price - trail

        :param trail_type:
        :param trail:
        :param action:
        :param price:
        :return:
        """
        if trail_type == constants.TRAIL_TYPE_VALUE:
            if action == constants.TRADE_ACTION_BUY:
                return price + trail
            elif action == constants.TRADE_ACTION_SELL:
                return price - trail
        elif trail_type == constants.TRAIL_TYPE_PERCENTAGE:
            if action == constants.TRADE_ACTION_BUY:
                return price + (price * trail / 100)
            elif action == constants.TRADE_ACTION_SELL:
                return price - (price * trail / 100)

    def create_limit_order(self, order: Order):
        # Add order into order book
        new_order = pd.DataFrame(
            {
                "order_id": order.order_id,
                "order_date": order.order_date,
                "ticker": order.ticker,
                "order_type": order.order_type,
                "action": order.action,
                "limit_price": order.limit_price,
                "time_in_force": order.time_in_force,
                "quantity": order.quantity,
                "stop_price": order.stop_price,
                "trail_type": order.trail_type,
                "trail": order.trail,
                "attached_order": order.attached_order,
                "status": constants.ORDER_STATUS_PENDING,
                "comments": "",
                "filled_date": "",
            },
            index=[0],
        )

        new_order["order_date"] = pd.to_datetime(new_order["order_date"])
        if self.order_book.empty:
            self.order_book = new_order
        else:
            self.order_book = pd.concat([self.order_book, new_order], ignore_index=True)

    def backtest(self):
        # Create StockEntity for each stock and store in the stocks dictionary
        for stock in self.order_book["ticker"].unique():
            self.stocks[stock] = StockEntity(symbol=stock)

        for current_timestamp, row in tqdm(self.ohlvc.iterrows(), total=len(self.ohlvc)):
            # Convert current_timestamp to pd.Timestamp type
            current_timestamp = typing.cast(pd.Timestamp, current_timestamp)
            # Fetch all pending orders that are earlier or equal to the current timestamp and status not filled or cancelled
            active_orders = self.order_book[
                (self.order_book["order_date"] <= current_timestamp)
                & (self.order_book["status"] != constants.ORDER_STATUS_FILLED)
                & (self.order_book["status"] != constants.ORDER_STATUS_CANCELLED)
                & (self.order_book["status"] != constants.ORDER_STATUS_EXPIRED)
            ]
            # Using while loop because there are additional orders created and appended into the active_orders df
            while len(active_orders) != 0:
                idx = active_orders.head(1).index[0]
                order = active_orders.loc[idx]

                # Fetch Order Details
                order_id = order["order_id"]
                date = order["order_date"]
                symbol = order["ticker"]
                order_type = order["order_type"]
                action = order["action"]
                limit_price = order["limit_price"]
                stop_price = order["stop_price"]
                quantity = order["quantity"]
                trail_type = order["trail_type"]
                trail = order["trail"]
                time_in_force = order["time_in_force"]
                attached_order = order["attached_order"]
                order_status = False
                msg = ""

                stock_entity = self.stocks[symbol]

                """
                Unattached Order: Orders that are sent to the market without any attached orders
                Example: 
                1. Long Position: BUY 100 AAPL @ 150
                2. Short Position: SELL 100 AAPL @ 170
                
                Attached Order: Orders that are tagged to an order to act like the stop loss / take profit orders
                Example:
                1. BUY 100 AAPL @ 150 (Unattached Order)
                2. Attached a sell order to the BUY order to sell 100 AAPL @ 170 (Attached Order)
                3. Attached a stop limit order to the BUY order to create a limit order of 125 when price goes under 130 (Attached Order)
                    a. When price reaches 130 --> Stop Limit Order is triggered and a Stop Limit order is created @ 125
                    b. When price reaches 125 --> Stop Limit Order is executed
                """

                if attached_order:
                    # If it is a Day order, check if the order is still valid
                    if time_in_force == constants.TIME_IN_FORCE_DAY:
                        if current_timestamp.date() != order["order_date"].date():
                            self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_EXPIRED
                            self.order_book.loc[idx, "comments"] = "Order Expired"
                            self.order_book.loc[idx, "filled_date"] = current_timestamp
                            continue

                    if order_type == constants.LIMIT_ORDER:
                        order_status, msg = stock_entity.limit_order(
                            trade=Trade(
                                date=date,
                                symbol=symbol,
                                order_type=order_type,
                                action=action,
                                limit_price=limit_price,
                                quantity=quantity,
                            ),
                            high_price=row[symbol]["High"],
                            low_price=row[symbol]["Low"],
                        )
                    elif order_type in constants.STOP_LOST_TRIGGERS:
                        if action == constants.TRADE_ACTION_BUY:
                            if self.stop_loss_trigger(stop_price=stop_price, action=action, price=row[symbol]["High"]):
                                self.create_limit_order(
                                    Order(
                                        order_id=order_id,
                                        attached_order=True,
                                        order_date=current_timestamp.strftime(format="%Y-%m-%d"),
                                        ticker=symbol,
                                        order_type=constants.LIMIT_ORDER,
                                        action=constants.TRADE_ACTION_BUY,
                                        limit_price=limit_price,
                                        time_in_force=constants.TIME_IN_FORCE_GTC,  # Defaults to GTC order for now
                                        quantity=quantity,
                                    )
                                )
                                # Update the status of the current order to "Filled"
                                self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_FILLED
                                self.order_book.loc[idx, "filled_date"] = current_timestamp
                                new_order = self.order_book.tail(1)
                                active_orders = pd.concat([active_orders, new_order])

                            elif order_type == constants.TRAILING_STOP_ORDER:
                                # TODO: check if we need to see if it is triggered on the same day or not
                                new_stop_price = self.update_trailing_stop_price(
                                    trail_type=trail_type, trail=trail, action=action, price=row[symbol]["High"]
                                )
                                self.order_book.at[idx, "stop_price"] = min(new_stop_price, stop_price)
                                self.order_book.at[idx, "limit_price"] = min(
                                    new_stop_price, stop_price
                                )  # limit price set to stop price for now

                        else:
                            if self.stop_loss_trigger(stop_price=stop_price, action=action, price=row[symbol]["Low"]):
                                self.create_limit_order(
                                    Order(
                                        order_id=order_id,
                                        attached_order=True,
                                        order_date=current_timestamp.strftime(format="%Y-%m-%d"),
                                        ticker=symbol,
                                        order_type=constants.LIMIT_ORDER,
                                        action=constants.TRADE_ACTION_SELL,
                                        limit_price=limit_price,
                                        time_in_force=constants.TIME_IN_FORCE_GTC,  # Defaults to GTC order for now
                                        quantity=quantity,
                                    )
                                )
                                # Update the status of the current order to "Filled"
                                self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_FILLED
                                self.order_book.loc[idx, "filled_date"] = current_timestamp
                                # Append the new order to the active orders df
                                new_order = self.order_book.tail(1)
                                active_orders = pd.concat([active_orders, new_order])

                            elif order_type == constants.TRAILING_STOP_ORDER:
                                # TODO: check if we need to see if it is triggered on the same day or not
                                new_stop_price = self.update_trailing_stop_price(
                                    trail_type=trail_type, trail=trail, action=action, price=row[symbol]["High"]
                                )
                                self.order_book.at[idx, "stop_price"] = max(new_stop_price, stop_price)
                                self.order_book.at[idx, "limit_price"] = max(
                                    new_stop_price, stop_price
                                )  # limit price set to stop price for now

                    # Check if attached order is filled
                    if order_status:
                        self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_FILLED
                        self.order_book.loc[idx, "filled_date"] = current_timestamp
                        # Find index of the other attached_order with the same order id and update status to cancelled
                        attached_order_idx_list = self.order_book[
                            (self.order_book["order_id"] == order_id)
                            & (self.order_book["status"] == constants.ORDER_STATUS_PENDING)
                        ].index.tolist()
                        if len(attached_order_idx_list) != 0:
                            for order_idx in attached_order_idx_list:
                                self.order_book.loc[order_idx, "status"] = constants.ORDER_STATUS_CANCELLED
                                self.order_book.loc[order_idx, "comments"] = "Attached Order Cancelled"
                                self.order_book.loc[order_idx, "filled_date"] = current_timestamp

                else:
                    # If it is a Day order, check if the order is still valid
                    if time_in_force == constants.TIME_IN_FORCE_DAY:
                        if current_timestamp.date() != order["order_date"].date():
                            self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_EXPIRED
                            self.order_book.loc[idx, "comments"] = "Order Expired"
                            self.order_book.loc[idx, "filled_date"] = current_timestamp
                            continue

                        if order_type == constants.LIMIT_ORDER:
                            order_status, msg = stock_entity.limit_order(
                                trade=Trade(
                                    date=date,
                                    symbol=symbol,
                                    order_type=order_type,
                                    action=action,
                                    limit_price=limit_price,
                                    quantity=quantity,
                                ),
                                high_price=row[symbol]["High"],
                                low_price=row[symbol]["Low"],
                            )

                        if order_status:
                            self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_FILLED
                            self.order_book.loc[idx, "filled_date"] = current_timestamp
                            # Find the attached orders and mark the status and pending
                            attached_order_idx_list = self.order_book[
                                (self.order_book["order_id"] == order_id) & (self.order_book.index != idx)
                            ].index.tolist()
                            if len(attached_order_idx_list) != 0:
                                # Send all the attached orders to "Pending"
                                for order_idx in attached_order_idx_list:
                                    self.order_book.loc[order_idx, "status"] = constants.ORDER_STATUS_PENDING
                                    self.order_book.loc[order_idx, "order_date"] = current_timestamp

                        else:
                            self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_CANCELLED
                            self.order_book.loc[idx, "comments"] = msg
                            self.order_book.loc[idx, "filled_date"] = current_timestamp
                            # Cancel the attached orders
                            attached_order_idx_list = self.order_book[
                                (self.order_book["order_id"] == order_id) & (self.order_book.index != idx)
                            ].index.tolist()
                            if len(attached_order_idx_list) != 0:
                                # Send all the attached orders to "Cancelled"
                                for order_idx in attached_order_idx_list:
                                    self.order_book.loc[order_idx, "status"] = constants.ORDER_STATUS_CANCELLED
                                    self.order_book.loc[order_idx, "filled_date"] = current_timestamp
                                    self.order_book.loc[order_idx, "comments"] = "Original Order Cancelled"

                    elif time_in_force == constants.TIME_IN_FORCE_GTC:
                        if order_type == constants.LIMIT_ORDER:
                            if order_type == constants.LIMIT_ORDER:
                                order_status, msg = stock_entity.limit_order(
                                    trade=Trade(
                                        date=date,
                                        symbol=symbol,
                                        order_type=order_type,
                                        action=action,
                                        limit_price=limit_price,
                                        quantity=quantity,
                                    ),
                                    high_price=row[symbol]["High"],
                                    low_price=row[symbol]["Low"],
                                )
                        if order_status:
                            self.order_book.loc[idx, "status"] = constants.ORDER_STATUS_FILLED
                            self.order_book.loc[idx, "filled_date"] = current_timestamp
                            # Find the attached orders and mark the status and pending
                            attached_order_idx_list = self.order_book[
                                (self.order_book["order_id"] == order_id) & (self.order_book.index != idx)
                            ].index.tolist()
                            if len(attached_order_idx_list) != 0:
                                for order_idx in attached_order_idx_list:
                                    self.order_book.loc[order_idx, "status"] = constants.ORDER_STATUS_PENDING
                                    self.order_book.loc[order_idx, "order_date"] = current_timestamp
                # Remove row from df
                active_orders = active_orders.drop(index=idx)
