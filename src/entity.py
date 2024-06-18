from dataclasses import dataclass
from typing import List

import pandas as pd

from src import constants


@dataclass
class Trade:
    entry_date: str = ""
    position_type: str = ""
    entry_action: str = ""
    entry_price: float = 0.0
    quantity: int = 0
    entry_fees: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    trailing_stop: float = 0.0
    trade_status: str = ""
    exit_date: str = ""
    exit_action: str = ""
    exit_price: float = 0.0
    exit_fees: float = 0.0
    trigger: str = ""
    pnl: float = 0.0


@dataclass
class HistoricalRecord:
    date: str
    adjusted_close: float
    quantity: int
    value: float


class StockEntity:
    TRADE_COLUMNS = [
        "entry_date",
        "position_type",
        "entry_action",
        "entry_price",
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

    HISTORICAL_RECORD_COLUMNS = [
        "date",
        "adjusted_close",
        "long_position_quantity",
        "short_position_quantity",
        "value",
    ]

    def __init__(self, symbol: str, commission: float):
        self.symbol = symbol
        self.commission = commission
        self.trades = self._initialize_dataframe(self.TRADE_COLUMNS)
        self.historical_records = self._initialize_dataframe(
            self.HISTORICAL_RECORD_COLUMNS
        )

    @staticmethod
    def _initialize_dataframe(columns: List[str]) -> pd.DataFrame:
        return pd.DataFrame(columns=columns)

    @staticmethod
    def calculate_pnl(
        entry_quantity,
        entry_price,
        exit_quantity,
        exit_price,
        entry_fees,
        exit_fees,
        position_type,
    ):
        # TODO: check if pnl should include calculation for fees
        if position_type == constants.LONG_POSITION:
            return (
                (exit_quantity * exit_price)
                - (entry_quantity * entry_price)
                - entry_fees
                - exit_fees
            )
        else:
            return (
                (entry_quantity * entry_price)
                - (exit_quantity * exit_price)
                - entry_fees
                - exit_fees
            )

    def buy(self, trade: Trade, open_position: int = None):
        if not isinstance(open_position, int):
            # No open position, add new row to add new trade
            if self.trades.empty:
                self.trades = pd.DataFrame([trade.__dict__])
            else:
                new_trade = pd.DataFrame([trade.__dict__]).dropna(axis=1)
                self.trades = pd.concat([self.trades, new_trade], ignore_index=True)
        else:
            # Create a DataFrame from the trade object
            self.update_trade_status(
                index=open_position,
                exit_date=trade.exit_date,
                exist_action=trade.exit_action,
                exit_price=trade.exit_price,
                exit_fees=trade.exit_fees,
                new_status=trade.trade_status,
                trigger=trade.trigger,
            )

    def sell(self, trade: Trade, open_position: int = None):
        if not isinstance(open_position, int):
            # No open position, add new row to add new trade
            if self.trades.empty:
                self.trades = pd.DataFrame([trade.__dict__])
            else:
                new_trade = pd.DataFrame([trade.__dict__]).dropna(axis=1)
                self.trades = pd.concat([self.trades, new_trade], ignore_index=True)
        else:
            self.update_trade_status(
                index=open_position,
                exit_date=trade.exit_date,
                exist_action=trade.exit_action,
                exit_price=trade.exit_price,
                exit_fees=trade.exit_fees,
                new_status=trade.trade_status,
                trigger=trade.trigger,
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
        self.trades.at[index, "exit_date"] = exit_date
        self.trades.at[index, "exit_action"] = exist_action
        self.trades.at[index, "exit_price"] = exit_price
        self.trades.at[index, "exit_fees"] = exit_fees
        self.trades.at[index, "trade_status"] = new_status
        self.trades.at[index, "trigger"] = trigger

        # Update PnL
        entry_quantity = self.trades.at[index, "quantity"]
        entry_price = self.trades.at[index, "entry_price"]
        exit_quantity = entry_quantity
        exit_price = self.trades.at[index, "exit_price"]

        self.trades.at[index, "pnl"] = self.calculate_pnl(
            entry_quantity,
            entry_price,
            exit_quantity,
            exit_price,
            self.trades.at[index, "entry_fees"],
            exit_fees,
            self.trades.at[index, "position_type"],
        )

    def update_historical_records(self, date, adjusted_close):
        open_trades = self.trades[
            self.trades["trade_status"] == constants.TRADE_STATUS_OPEN
        ]

        long_qty = open_trades[open_trades["position_type"] == constants.LONG_POSITION][
            "quantity"
        ].sum()

        short_qty = open_trades[
            open_trades["position_type"] == constants.SHORT_POSITION
        ]["quantity"].sum()

        # TODO: check how to calculate value if there is both long and short positions
        value = (adjusted_close * long_qty) - (adjusted_close * short_qty)

        new_record = {
            "date": date,
            "adjusted_close": adjusted_close,
            "long_position_quantity": long_qty,
            "short_position_quantity": short_qty,
            "value": value,
        }

        if self.historical_records.empty:
            self.historical_records = pd.DataFrame([new_record])
        else:
            self.historical_records = pd.concat(
                [self.historical_records, pd.DataFrame([new_record])], ignore_index=True
            )

    def stats(self):
        total_fees = self.trades["entry_fees"].sum() + self.trades["exit_fees"].sum()
        net_position = self.trades[self.trades["trade_status"] == constants.TRADE_STATUS_OPEN]["quantity"].sum()
        pnl = self.trades["pnl"].sum()
        return {
            "symbol": self.symbol,
            "total_fees": total_fees,
            "net_position": net_position,
            "pnl": pnl,
        }

    def get_trades(self):
        return self.trades

    def get_historical_records(self):
        return self.historical_records

    def get_open_position(self):
        return self.trades[self.trades["trade_status"] == constants.TRADE_STATUS_OPEN]