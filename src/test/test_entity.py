import pandas as pd
import pytest

from src.entity import StockEntity, Trade


class TestEntity:
    @pytest.fixture
    def stock_entity(self):
        return StockEntity(symbol="AAPL", commission=0.02)

    def get_long_trade(self):
        return Trade(
            entry_date="2020-01-01",
            position_type="long",
            entry_action="buy",
            entry_price=100,
            quantity=100,
            entry_fees=2,
            stop_loss=98,
            take_profit=102,
            trailing_stop=0.02,
            trade_status="open",
        )

    def get_close_long_trade(self):
        return Trade(
            exit_date="2020-01-02",
            exit_action="sell",
            exit_price=102,
            exit_fees=2,
            trigger="take_profit",
            trade_status="closed",
        )

    def get_short_trade(self):
        return Trade(
            entry_date="2020-01-01",
            position_type="short",
            entry_action="sell",
            entry_price=100,
            quantity=100,
            entry_fees=2,
            stop_loss=102,
            take_profit=98,
            trailing_stop=0.02,
            trade_status="open",
        )

    def get_close_short_trade(self):
        return Trade(
            exit_date="2020-01-02",
            exit_action="buy",
            exit_price=98,
            exit_fees=2,
            trigger="take_profit",
            trade_status="closed",
        )

    def test_stock_entity(self, stock_entity):
        assert stock_entity.symbol == "AAPL"
        assert stock_entity.commission == 0.02

    def test_stock_entity_buy(self, stock_entity):
        trade_object = self.get_long_trade()
        stock_entity.buy(trade_object)

        assert len(stock_entity.trades) == 1
        assert stock_entity.trades["trade_status"].iloc[0] == "open"
        assert stock_entity.trades["entry_date"].iloc[0] == "2020-01-01"
        assert stock_entity.trades["position_type"].iloc[0] == "long"
        assert stock_entity.trades["entry_action"].iloc[0] == "buy"
        assert stock_entity.trades["entry_price"].iloc[0] == 100
        assert stock_entity.trades["quantity"].iloc[0] == 100
        assert stock_entity.trades["entry_fees"].iloc[0] == 2
        assert stock_entity.trades["stop_loss"].iloc[0] == 98
        assert stock_entity.trades["take_profit"].iloc[0] == 102
        assert stock_entity.trades["trailing_stop"].iloc[0] == 0.02

    def test_stock_entity_close_long_trade(self, stock_entity):
        trade_object = self.get_long_trade()
        stock_entity.buy(trade_object)
        trade_object = self.get_close_long_trade()
        stock_entity.sell(trade_object, open_position=0)
        assert len(stock_entity.trades) == 1
        assert stock_entity.trades["trade_status"].iloc[0] == "closed"
        assert stock_entity.trades["exit_date"].iloc[0] == "2020-01-02"
        assert stock_entity.trades["exit_action"].iloc[0] == "sell"
        assert stock_entity.trades["exit_price"].iloc[0] == 102
        assert stock_entity.trades["exit_fees"].iloc[0] == 2
        assert stock_entity.trades["trigger"].iloc[0] == "take_profit"
        assert stock_entity.trades["pnl"].iloc[0] == 196

    def test_stock_entity_sell(self, stock_entity):
        trade_object = self.get_short_trade()
        stock_entity.sell(trade_object)
        assert len(stock_entity.trades) == 1
        assert stock_entity.trades["trade_status"].iloc[0] == "open"
        assert stock_entity.trades["entry_date"].iloc[0] == "2020-01-01"
        assert stock_entity.trades["position_type"].iloc[0] == "short"
        assert stock_entity.trades["entry_action"].iloc[0] == "sell"
        assert stock_entity.trades["entry_price"].iloc[0] == 100
        assert stock_entity.trades["quantity"].iloc[0] == 100
        assert stock_entity.trades["entry_fees"].iloc[0] == 2
        assert stock_entity.trades["stop_loss"].iloc[0] == 102
        assert stock_entity.trades["take_profit"].iloc[0] == 98
        assert stock_entity.trades["trailing_stop"].iloc[0] == 0.02

    def test_stock_entity_close_short_trade(self, stock_entity):
        trade_object = self.get_short_trade()
        stock_entity.sell(trade_object)
        trade_object = self.get_close_short_trade()
        stock_entity.buy(trade_object, open_position=0)
        assert len(stock_entity.trades) == 1
        assert stock_entity.trades["trade_status"].iloc[0] == "closed"
        assert stock_entity.trades["exit_date"].iloc[0] == "2020-01-02"
        assert stock_entity.trades["exit_action"].iloc[0] == "buy"
        assert stock_entity.trades["exit_price"].iloc[0] == 98
        assert stock_entity.trades["exit_fees"].iloc[0] == 2
        assert stock_entity.trades["trigger"].iloc[0] == "take_profit"
        assert stock_entity.trades["pnl"].iloc[0] == 196

    @pytest.mark.parametrize(
        "entry_quantity, entry_price, exit_quantity, exit_price, entry_fees, exit_fees, position_type, expected_result",
        [
            (100, 100, 100, 110, 0, 0, "long", 1000),
            (100, 100, 100, 90, 0, 0, "short", 1000),
            (100, 100, 100, 90, 0, 0, "long", -1000),
            (100, 100, 100, 110, 0, 0, "short", -1000),
        ],
    )
    def test_stock_entity_calculate_pnl(
        self,
        stock_entity,
        entry_quantity,
        entry_price,
        exit_quantity,
        exit_price,
        entry_fees,
        exit_fees,
        position_type,
        expected_result,
    ):

        assert (
            stock_entity.calculate_pnl(
                entry_quantity,
                entry_price,
                exit_quantity,
                exit_price,
                entry_fees,
                exit_fees,
                position_type,
            )
            == expected_result
        )

    def test_stock_entity_update_historical_position(self):
        pass

    def test_stock_entity_get_trades(self, stock_entity):
        assert isinstance(stock_entity.get_trades(), pd.DataFrame)

    def test_stock_entity_get_historical_records(self, stock_entity):
        assert isinstance(stock_entity.get_historical_records(), pd.DataFrame)
