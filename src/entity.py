from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional

import pandas as pd

from src import constants


@dataclass
class Trade:
    date: str
    symbol: str
    order_type: str
    action: str
    limit_price: float
    quantity: float


@dataclass
class HistoricalRecord:
    date: str
    adjusted_close: float
    quantity: int
    value: float


class StockEntity:
    TRADE_COLUMNS = [
        "date",
        "symbol",
        "order_type",
        "action",
        "limit_price",
        "quantity",
    ]

    HISTORICAL_RECORD_COLUMNS = [
        "date",
        "adjusted_close",
        "long_position_quantity",
        "short_position_quantity",
        "value",
    ]

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.trades = self._initialize_dataframe(self.TRADE_COLUMNS)
        # self.historical_records = self._initialize_dataframe(
        #     self.HISTORICAL_RECORD_COLUMNS
        # )

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
            return (exit_quantity * exit_price) - (entry_quantity * entry_price) - entry_fees - exit_fees
        else:
            return (entry_quantity * entry_price) - (exit_quantity * exit_price) - entry_fees - exit_fees

    # TODO: Add a method for Limit Order, Stop Order and Market Order
    def limit_order(
        self,
        trade: Trade,
        high_price: float,
        low_price: float,
    ) -> Tuple[bool, str]:
        if trade.action == constants.TRADE_ACTION_BUY:
            if trade.limit_price >= low_price:
                self.update_trades(trade)
                return True, ""
        elif trade.action == constants.TRADE_ACTION_SELL:
            if trade.limit_price <= high_price:
                self.update_trades(trade)
                return True, ""

        return False, "Ask/Bid price is not met"

    def market_order(self, trade: Trade):
        pass

    def update_trades(self, trade: Trade):
        # No open position, add new row to add new trade
        if self.trades.empty:
            self.trades = pd.DataFrame([trade.__dict__])
        else:
            new_trade = pd.DataFrame([trade.__dict__]).dropna(axis=1)
            self.trades = pd.concat([self.trades, new_trade], ignore_index=True)
