import pytest
from src.backtest_engine import BacktestEngine
import pandas as pd
from src import constants
from src.ibkr_fees import calculate_ibkr_fixed_cost


class TestBacktestEngine:
    # Set up a BacktestEngine instance for testing
    @pytest.fixture
    def backtest_engine(self):
        trade_orders = pd.DataFrame(
            {
                "stock": ["AAPL"],
                "date": ["2020-01-01"],
                "quantity": [100],
                "price": [100],
                "position_type": ["long"],
                "order_type": ["market"],
                "stop_loss": [98],
                "take_profit": [102],
                "trailing_stop": [0.02],  # TODO: to confirm this
                "duration": ["Day"], #TODO: see if we need to support this function
            }
        )
        ohlvc = pd.DataFrame(
            {"Date": ["2020-01-01"], "High": [105], "Low": [95], "Close": [100]}
        )
        return BacktestEngine(trade_orders, ohlvc)

    def test_calculate_fees(self, backtest_engine):
        # Test the calculate_fees method
        price = 100
        quantity = 10
        expected_fees = calculate_ibkr_fixed_cost(qty=quantity, price_per_share=price)
        calculated_fees = backtest_engine.calculate_fees(price, quantity)
        assert calculated_fees == expected_fees

    @pytest.mark.parametrize(
        "high_price, low_price, stop_loss, position_type, expected_result",
        [
            (105, 95, 96, constants.LONG_POSITION, True),
            (105, 95, 104, constants.SHORT_POSITION, True),
            (105, 95, 94, constants.LONG_POSITION, False),
            (105, 95, 110, constants.SHORT_POSITION, False),
        ],
    )
    def test_stop_loss_triggered(
        self,
        backtest_engine,
        high_price,
        low_price,
        stop_loss,
        position_type,
        expected_result,
    ):
        assert (
            backtest_engine.stop_loss_triggered(
                high_price, low_price, stop_loss, position_type
            )
            == expected_result
        )

    @pytest.mark.parametrize(
        "high_price, low_price, take_profit, position_type, expected_result",
        [
            (105, 95, 104, constants.LONG_POSITION, True),
            (105, 95, 96, constants.SHORT_POSITION, True),
            (105, 95, 106, constants.LONG_POSITION, False),
            (105, 95, 94, constants.SHORT_POSITION, False),
        ],
    )
    def test_take_profit_triggered(
        self,
        backtest_engine,
        high_price,
        low_price,
        take_profit,
        position_type,
        expected_result,
    ):
        assert (
            backtest_engine.take_profit_triggered(
                high_price, low_price, take_profit, position_type
            )
            == expected_result
        )
