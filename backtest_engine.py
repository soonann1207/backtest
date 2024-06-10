import pandas as pd
from tqdm import tqdm

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

"""
Questions: 
1. Does the buy and sell order need to match? 
E.g. 1 Order: Buy 5 Stock, Sell 5 Stock / Sell 5 Stock, Buy 5 Stock --> Order = Closed
What happens when there is a scenario where we buy 5 stock and sell 10 stock?
Does it become Order 1: Buy 5, Sell 5 : Order Closes & Order 2: Sell 5 : Order Opens?

Or will it become
Order 1: Buy 5 Stock, when TP/SL trigger --> Sell 5 Stock: Order Closed
Order 2: Sell 10 Stock, when TP/SL trigger --> Buy 10 Stock: Order Closed

2. Will there be a case where there is different stop loss, take profit, trailing stop 
for the same stock of different orders

3. What frequency will the backtest need to support? Daily / Hourly / Minute? 

4. For the trailing stop loss, how do we determine the price to use to calculate the trailing stop price?
E.g: If we are testing on a daily basis, do we use the high and low price of the day to calculate the trailing stop price?
How would we know if the low price comes before the high price?
Or do we take the close price of the prev day and use it to calculate the trailing stop price? 
Then use the high and low to calculate the trailing stop price

5. How should we calculate remaining capital when we are executing a short? 
Does the capital increase from the short sale? 
Is there a % of the short sale that is held as collateral?

6. Should we use the volume of the stocks to determine if the trade can be executed?
"""


class BacktestEngine:
    def __init__(
        self,
        trade_orders,
        ohlc,
        commission=0.02,
        # slippage=0.0,
        initial_capital=100000.0,
    ):
        self.trade_orders = trade_orders
        self.ohlc = ohlc
        self.commission = commission
        # self.slippage = slippage
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trade_records = pd.DataFrame(
            data=[],
            columns=[
                "date",
                "stock",
                "quantity",
                "signal_type",
                "price",
                "fees",
                "status",
                "stop_loss",
                "take_profit",
                "trailing_stop",
            ],
        )
        self.trade_positions = pd.DataFrame(
            data=[],
            columns=[
                "date",
                "stock",
                "quantity",
                "average_price",
                "current_value",
                "close_price",
                "pnl",
                "stop_loss",
                "take_profit",
                "trailing_stop",
            ],
            # columns=[
            #     "date",
            #     "stock",
            #     "entry_timestamp",
            #     "entry_price",
            #     "entry_size",
            #     "entry_fee",
            #     "exit_timestamp",
            #     "exit_price",
            #     "exit_size",
            #     "exit_fee",
            #     "unrealized_pnl",
            #     "realized_pnl",
            #     "order_status",
            # ],
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

    def update_trade_record(
        self,
        date,
        stock,
        quantity,
        signal_type,
        price,
        fees,
        # order_type,
        status,
        stop_loss,
        take_profit,
        trailing_stop,
        # duration,
    ):
        new_trade_record = pd.DataFrame(
            {
                "date": date,
                "stock": stock,
                "quantity": quantity,
                "signal_type": signal_type,
                "price": price,
                "fees": fees,
                # "order_type": order_type,
                "status": status,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "trailing_stop": trailing_stop,
                # "duration": duration,
            },
            index=[0],
        )
        self.trade_records = pd.concat(
            [self.trade_records, new_trade_record], ignore_index=True
        )

    def buy(
        self,
        date,
        stock,
        quantity,
        price,
        close_price,
        high_price,
        low_price,
        stop_loss=0.0,
        take_profit=0.0,
        trailing_stop=0.0,
        # duration=None,
    ):

        # Check if existing capital is enough to buy the stock with the given commission
        if self.current_capital < (quantity * price) + self.commission * (
            quantity * price
        ):

            print("Insufficient Capital")
            # Update DataFrame with the trade details
            self.update_trade_record(
                date=date,
                stock=stock,
                quantity=quantity,
                signal_type="Buy",
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                status="Cancelled",
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )
            return

        # Check if the price is higher than low price
        if price < low_price:
            print("Bid price is lower than low price")
            self.update_trade_record(
                date=date,
                stock=stock,
                quantity=quantity,
                signal_type="Buy",
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                status="Cancelled",
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )
            return

        # Execute the trade
        self.current_capital -= (quantity * price) + self.commission * (
            quantity * price
        )
        self.update_trade_record(
            date=date,
            stock=stock,
            quantity=quantity,
            signal_type="Buy",
            price=price,
            fees=self.commission * (quantity * price),
            # order_type="Market",
            status="Filled",
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            # duration=duration,
        )
        print("Trade Executed")

        return

    def sell(
        self,
        date,
        stock,
        quantity,
        price,
        close_price,
        high_price,
        low_price,
        stop_loss=0.0,
        take_profit=0.0,
        trailing_stop=0.0,
        # duration=None,
    ):
        # Check if existing capital is enough to sell the stock with the given commission
        if self.current_capital < self.commission * (quantity * price):  # TODO: check
            print("Insufficient Capital")
            self.update_trade_record(
                date=date,
                stock=stock,
                quantity=quantity,
                signal_type="Sell",
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                status="Cancelled",
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )
            return

        # Check if the price is lower than high price
        if price > high_price:
            print("Ask price is higher than high price")
            self.update_trade_record(
                date=date,
                stock=stock,
                quantity=quantity,
                signal_type="Sell",
                price=price,
                fees=self.commission * (quantity * price),
                # order_type="Market",
                status="Cancelled",
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                # duration=duration,
            )
            return

        # Execute the trade
        self.current_capital += (quantity * price) - self.commission * (
            quantity * price
        )
        self.update_trade_record(
            date=date,
            stock=stock,
            quantity=quantity,
            signal_type="Sell",
            price=price,
            fees=self.commission * (quantity * price),
            # order_type="Market",
            status="Filled",
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            # duration=duration,
        )
        print("Trade Executed")

        return

    def update_trade_positions(self, current_datetime, close_price):
        """
        Update the trade positions DataFrame
        Logic:
            1. Loop through the trade records
            2. Calculate the average price and PnL for each stock/order
            3. Update the trade positions DataFrame
        """
        for stock in self.trade_records["stock"].unique():
            stock_trades = self.trade_records.loc[self.trade_records["stock"] == stock]
            stock_trades = stock_trades.loc[stock_trades["status"] == "Filled"]

            # calculate the total quantity given Buy and Sell signal types
            buy_quantity = stock_trades.loc[
                stock_trades["signal_type"] == "Buy", "quantity"
            ].sum()
            sell_quantity = stock_trades.loc[
                stock_trades["signal_type"] == "Sell", "quantity"
            ].sum()

            total_quantity = buy_quantity - sell_quantity
            # take in current price
            value = total_quantity * close_price

            # Stop Loss, Take Profit, Trailing Stop
            stop_loss = stock_trades["stop_loss"].iloc[-1]
            take_profit = stock_trades["take_profit"].iloc[-1]
            trailing_stop = stock_trades["trailing_stop"].iloc[-1]

            new_trade_position = pd.DataFrame(
                {
                    "date": current_datetime,
                    "stock": stock,
                    "quantity": total_quantity,
                    "average_entry_price": 0,  # TODO: complete this calculation
                    "current_value": value,
                    "close_price": close_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "trailing_stop": trailing_stop,
                },
                index=[0],
            )
            self.trade_positions = pd.concat(
                [self.trade_positions, new_trade_position], ignore_index=True
            )

        return

    def stop_loss_triggered(self, trade_position, low_price, high_price):
        # Check if the trade has hit the stop loss
        if trade_position["stop_loss"] is not None:
            return False

        # Stop loss for long position
        if trade_position["quantity"] > 0:
            if low_price < trade_position["stop_loss"] * trade_position["price"]:
                return True

        # Stop loss for short position
        elif trade_position["quantity"] < 0:
            if high_price > trade_position["stop_loss"] * trade_position["price"]:
                return True

    def take_profit_triggered(self, trade_position, low_price, high_price):
        # Check if the trade has hit the take profit
        if trade_position["take_profit"] is not None:
            return False

        # Take profit for long position
        if trade_position["quantity"] > 0:
            if (
                high_price
                > (1 + trade_position["take_profit"]) * trade_position["price"]
            ):
                return True

        # Take profit for short position
        elif trade_position["quantity"] < 0:
            if (
                low_price
                < (1 + trade_position["take_profit"]) * trade_position["price"]
            ):
                return True

    # TODO: Check which prices to use to calculate current value of the stock
    #  --> used to determine trailing stop price
    def trailing_stop_triggered(self, trade_position, low_price, high_price):
        # Check if the trade has hit the trailing stop
        if trade_position["trailing_stop"] is not None:
            return False

        # Trailing stop for long position
        if trade_position["quantity"] > 0:
            if (
                low_price
                < (1 + trade_position["trailing_stop"]) * trade_position["price"]
            ):
                return True

        # Trailing stop for short position
        elif trade_position["quantity"] < 0:
            if (
                high_price
                > (1 + trade_position["trailing_stop"]) * trade_position["price"]
            ):
                return True

    def stop_loss(self, trade_position, high_price, low_price, close_price):
        # Stop loss for long position
        if trade_position["quantity"] > 0:
            self.buy(
                stock=trade_position["stock"],
                date=trade_position["date"],
                quantity=trade_position["quantity"],
                price=low_price,  # TODO: Check if price is correct
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
            )

        # Stop loss for short position
        elif trade_position["quantity"] < 0:
            self.sell(
                stock=trade_position["stock"],
                date=trade_position["date"],
                quantity=trade_position["quantity"]
                * -1,  # Short position will have negative quantity
                price=high_price,  # TODO: Check if price is correct
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
            )

    def take_profit(self, trade_position, high_price, low_price, close_price):
        # Take profit for long position
        if trade_position["quantity"] > 0:
            self.sell(
                stock=trade_position["stock"],
                date=trade_position["date"],
                quantity=trade_position["quantity"],
                price=high_price,  # TODO: Check if price is correct
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
            )

        # Take profit for short position
        elif trade_position["quantity"] < 0:
            self.buy(
                stock=trade_position["stock"],
                date=trade_position["date"],
                quantity=trade_position["quantity"]
                * -1,  # Short position will have negative quantity
                price=low_price,  # TODO: Check if price is correct
                close_price=close_price,
                high_price=high_price,
                low_price=low_price,
            )

    def trailing_stop(
        self, stock, date, quantity, price, duration, close_price, high_price, low_price
    ):
        pass

    def backtest(self):
        """
        Backtest the trade order
        Logic:
            1. Loop through each day in the price data
            2. Check if any existing trades has hit the stop loss, take profit or trailing stop
            3. Check if there are any new trades to be executed


        """
        days_with_orders = self.trade_orders.date.unique().tolist()
        for price_index, row in tqdm(self.ohlc.iterrows(), total=len(self.ohlc)):
            # Check if any existing trades has hit the stop loss, take profit or trailing stop
            # if not self.trade_positions.empty:
            #     for idx, trade_position in self.trade_positions.iterrows():
            #         # Check if the trade has hit the stop loss
            #         if trade_position["stop_loss"] != 0 & self.stop_loss_triggered(
            #             trade_position=trade_position,
            #             low_price=row["Low"],
            #             high_price=row["High"],
            #         ):
            #             print("Stop Loss Triggered")
            #             self.stop_loss(
            #                 trade_position, row["High"], row["Low"], row["Close"]
            #             )
            #
            #             # TODO: need to update trades_positions to reflect the stop loss
            #
            #         # Check if the trade has hit the take profit
            #         if trade_position["take_profit"] != 0 & self.take_profit_triggered(
            #             trade_position=trade_position,
            #             low_price=row["Low"],
            #             high_price=["High"],
            #         ):
            #             print("Take Profit Triggered")
            #             self.take_profit(
            #                 trade_position, row["High"], row["Low"], row["Close"]
            #             )
            #
            #             # TODO: need to update trades_positions to reflect the stop loss
            #
            #         # Check if the trade has hit the trailing stop
            #         if trade_position["trailing_stop"] != 0 & self.trailing_stop_triggered(
            #             trade_position, row["Low"], row["High"]
            #         ):
            #             print("Trailing Stop Triggered")
            #
            #             # TODO: need to update trades_positions to reflect the stop loss

            if row["Date"] in days_with_orders:
                trade_details = self.trade_orders.loc[
                    self.trade_orders["date"] == row["Date"]
                ].squeeze()
                stock = trade_details["stock"]
                date = trade_details["date"]
                quantity = trade_details["quantity"]
                price = trade_details["price"]
                signal_type = trade_details["signal_type"]
                # order_type = trade_details["order_type"]
                stop_loss = trade_details["stop_loss"]
                take_profit = trade_details["take_profit"]
                trailing_stop = trade_details["trailing_stop"]
                # duration = trade_details["duration"]

                if signal_type == "Buy":
                    self.buy(
                        date=date,
                        stock=stock,
                        quantity=quantity,
                        price=price,
                        close_price=self.ohlc["Close"].loc[price_index],
                        high_price=self.ohlc["High"].loc[price_index],
                        low_price=self.ohlc["Low"].loc[price_index],
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        trailing_stop=trailing_stop,
                        # duration=duration,
                    )
                elif signal_type == "Sell":
                    self.sell(
                        date=date,
                        stock=stock,
                        quantity=quantity,
                        price=price,
                        close_price=self.ohlc["Close"].loc[price_index],
                        high_price=self.ohlc["High"].loc[price_index],
                        low_price=self.ohlc["Low"].loc[price_index],
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        trailing_stop=trailing_stop,
                        # duration=duration,
                    )

            self.update_trade_positions(
                current_datetime=row["Date"], close_price=row["Close"]
            )
