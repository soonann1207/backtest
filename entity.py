import pandas as pd

import constants


class StockEntity:
    def __init__(self, symbol: str, commission: float):
        self.symbol = symbol
        self.commission = commission
        self.trades = pd.DataFrame(
            columns=[
                "entry_date",
                "position_type",
                "entry_action",
                "price",
                "quantity",
                "entry_fees",
                "stop_loss",
                "take_profit",
                "trailing_stop",
                "exit_date",
                "exit_action",
                "exit_price",
                "exit_fees",
                "trigger",
                "pnl",
                "trade_status",
            ]
        )
        self.historical_records = pd.DataFrame(
            columns=[
                "date",
                "adjusted_close",
                "quantity",
                "value",
            ]
        )

    def buy(
        self,
        entry_date,
        position_type: str,
        price: float,
        quantity: int,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float,
        trade_status: str = None,
    ):
        fees = self.commission * price * quantity
        new_transaction = {
            "entry_date": entry_date,
            "position_type": position_type,
            "entry_action": "buy",
            "price": price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "trailing_stop": trailing_stop,
            "entry_fees": fees,
            "trade_status": trade_status,
        }
        self.trades = pd.concat(
            [self.trades, pd.DataFrame([new_transaction])], ignore_index=True
        )

    def sell(
        self,
        entry_date,
        position_type: str,
        price: float,
        quantity: int,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float,
        trade_status: str = None,
    ):
        fees = self.commission * price * quantity
        new_transaction = {
            "entry_date": entry_date,
            "position_type": position_type,
            "entry_action": "sell",
            "price": price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "trailing_stop": trailing_stop,
            "entry_fees": fees,
            "trade_status": trade_status,
        }
        self.trades = pd.concat(
            [self.trades, pd.DataFrame([new_transaction])], ignore_index=True
        )

    def stop_loss_triggered(self, high_price, low_price, stop_loss, position_type):
        if position_type == constants.LONG_POSITION and low_price <= stop_loss:
            return True
        elif position_type == constants.SHORT_POSITION and high_price >= stop_loss:
            return True

    def stop_loss(self, date, high_price, low_price):
        open_trades = self.trades[
            self.trades["trade_status"] == constants.TRADE_STATUS_OPEN
        ]
        # print("Open Trades: ", open_trades)
        for index, row in open_trades.iterrows():
            if self.stop_loss_triggered(
                high_price, low_price, row["stop_loss"], row["position_type"]
            ):
                # Long Positions
                if row["position_type"] == constants.LONG_POSITION:
                    # Update exist action, exit price, trade status
                    fees = self.commission * row["stop_loss"] * row["quantity"]
                    self.update_trade_status(
                        index,
                        date,
                        "buy",
                        float(row["stop_loss"]),
                        fees,
                        constants.TRADE_STATUS_CLOSED,
                        constants.TRADE_TRIGGER_STOP_LOSS,
                    )

                # Short Positions
                elif row["position_type"] == constants.SHORT_POSITION:
                    fees = self.commission * row["stop_loss"] * row["quantity"]
                    self.update_trade_status(
                        index,
                        date,
                        "buy",
                        float(row["stop_loss"]),
                        fees,
                        constants.TRADE_STATUS_CLOSED,
                        constants.TRADE_TRIGGER_STOP_LOSS,
                    )

    def take_profit_triggered(self, high_price, low_price, take_profit, position_type):
        if position_type == constants.LONG_POSITION and high_price >= take_profit:
            return True
        elif position_type == constants.SHORT_POSITION and low_price <= take_profit:
            return True

    def take_profit(self, date, high_price, low_price):
        open_trades = self.trades[
            self.trades["trade_status"] == constants.TRADE_STATUS_OPEN
        ]
        for index, row in open_trades.iterrows():
            if self.take_profit_triggered(
                high_price, low_price, row["take_profit"], row["position_type"]
            ):
                # Long Positions
                if row["position_type"] == constants.LONG_POSITION:
                    # Update exist action, exit price, trade status
                    fees = self.commission * row["take_profit"] * row["quantity"]
                    self.update_trade_status(
                        index,
                        date,
                        "sell",
                        float(row["take_profit"]),
                        fees,
                        constants.TRADE_STATUS_CLOSED,
                        constants.TRADE_TRIGGER_TAKE_PROFIT,
                    )

                # Short Positions
                elif row["position_type"] == constants.SHORT_POSITION:
                    fees = self.commission * row["take_profit"] * row["quantity"]
                    self.update_trade_status(
                        index,
                        date,
                        "sell",
                        float(row["take_profit"]),
                        fees,
                        constants.TRADE_STATUS_CLOSED,
                        constants.TRADE_TRIGGER_TAKE_PROFIT,
                    )

    def update_trade_status(
        self,
        index,
        exit_date,
        exist_action,
        exit_price,
        exit_fees,
        new_status,
        trigger,
    ):
        # Update exit date
        self.trades.at[index, "exit_date"] = exit_date

        # Update exist action
        self.trades.at[index, "exit_action"] = exist_action

        # Update exit price
        self.trades.at[index, "exit_price"] = exit_price

        # Update exit fees
        self.trades.at[index, "exit_fees"] = exit_fees

        # Update trade status
        self.trades.at[index, "trade_status"] = new_status

        # Update trigger
        self.trades.at[index, "trigger"] = trigger

        # Update PnL
        entry_quantity = self.trades.at[index, "quantity"]
        entry_price = self.trades.at[index, "price"]
        entry_fees = self.trades.at[index, "entry_fees"]
        exit_quantity = entry_quantity
        exit_price = self.trades.at[index, "exit_price"]
        exit_fees = self.trades.at[index, "exit_fees"]
        self.trades.at[index, "pnl"] = self.calculate_pnl(
            entry_quantity,
            entry_price,
            exit_quantity,
            exit_price,
            entry_fees,
            exit_fees,
        )

    def calculate_pnl(
        self,
        entry_quantity,
        entry_price,
        exit_quantity,
        exit_price,
        entry_fees,
        exit_fees,
    ):
        return (exit_quantity * exit_price - exit_fees) - (
            entry_quantity * entry_price + entry_fees
        )

    def update_historical_records(self, date, adjusted_close):
        # Calculate quantity, value
        quantity = self.trades["quantity"].sum()
        value = adjusted_close * quantity

        new_record = {
            "date": date,
            "adjusted_close": adjusted_close,
            "quantity": quantity,
            "value": value,
        }
        self.historical_records = pd.concat(
            [self.historical_records, pd.DataFrame([new_record])], ignore_index=True
        )

    def stats(self):
        total_fees = self.trades["fees"].sum()
        net_position = self.trades["quantity"].sum()
        return {
            "symbol": self.symbol,
            "total_fees": total_fees,
            "net_position": net_position,
        }

    def get_trades(self):
        return self.trades

    def get_historical_records(self):
        return self.historical_records

    def get_position(self):
        # Return the current price, quantity, and the total value of the position
        current_price = self.trades["price"].iloc[
            -1
        ]  # TODO: use latest adjusted close price
        current_quantity = self.trades["quantity"].sum()
        position_value = current_price * current_quantity
        return {
            "symbol": self.symbol,
            "current_price": current_price,
            "current_quantity": current_quantity,
            "position_value": position_value,
        }
