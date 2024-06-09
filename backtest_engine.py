import pandas as pd
import yfinance as yf

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
    def __init__(self, trade_order, ohlc, commission=0.02, slippage=0.0, initial_capital=100000.0):
        self.trade_order = trade_order
        self.ohlc = ohlc
        self.commission = commission
        self.slippage = slippage
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trade_records = pd.DataFrame(data=[], columns=['date', 'stock', 'quantity', 'signal_type', 'price', 'fee',
                                                            'status'])
        self.trade_positions = pd.DataFrame(data=[],
                                            columns=['date', 'stock', 'quantity', 'average_price', 'pnl', 'value'])

        '''
        Trade Records to track all the BUY & SELL transactions
        Date: Date of the transaction
        Stock: Stock symbol
        Quantity: Number of shares bought/sold
        Price: Price at which the transaction was made
        Fee: Commission charged for the transaction
        Status: Filled/Cancelled
        '''

    def buy(self, stock, date, quantity, price, duration, close_price, high_price, low_price):

        # Check if existing capital is enough to buy the stock with the given commission
        if self.current_capital < (quantity * price) + self.commission * (quantity * price):
            print('Insufficient Capital')
            # Update DataFrame with the trade details
            new_trade_record = pd.DataFrame({'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Buy',
                                             'price': price, 'fee': self.commission,
                                             'status': 'Cancelled'}, index=[0])
            self.trade_records = pd.concat([self.trade_records, new_trade_record], ignore_index=True)

            return

        # Check if the price is higher than low price
        if price < low_price:
            print('Price is lower than low price')
            new_trade_record = pd.DataFrame(
                {'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Buy', 'price': price,
                 'fee': self.commission, 'status': 'Cancelled'}, index=[0])
            self.trade_records = pd.concat([self.trade_records, new_trade_record], ignore_index=True)

            return

        # Execute the trade
        self.current_capital -= (quantity * price) + self.commission * (quantity * price)
        new_trade_record = pd.DataFrame(
            {'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Buy', 'price': price,
             'fee': self.commission, 'status': 'Filled'}, index=[0])
        self.trade_records = pd.concat([self.trade_records, new_trade_record], ignore_index=True)

        print('Trade Executed')

        return

    def sell(self, stock, date, quantity, price, duration, close_price, high_price, low_price):
        # Check if existing capital is enough to sell the stock with the given commission
        if self.current_capital < self.commission * (quantity * price):
            print('Insufficient Capital')
            new_trade_record = pd.DataFrame(
                {'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Sell', 'price': price,
                 'fee': self.commission, 'status': 'Cancelled'}, index=[0])
            return

        # Check if the price is lower than high price
        if price > high_price:
            print('Price is higher than high price')
            new_trade_record = pd.DataFrame(
                {'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Sell', 'price': price,
                 'fee': self.commission, 'status': 'Cancelled'}, index=[0])
            return

        # Execute the trade
        self.current_capital += (quantity * price) - self.commission * (quantity * price)
        new_trade_record = pd.DataFrame(
            {'date': date, 'stock': stock, 'quantity': quantity, 'signal_type': 'Sell', 'price': price,
             'fee': self.commission, 'status': 'Filled'}, index=[0])
        self.trade_records = pd.concat([self.trade_records, new_trade_record], ignore_index=True)

        return

    def update_trade_positions(self, current_datetime, close_price):
        '''
        Update the trade positions DataFrame
        Logic:
            1. Loop through the trade records
            2. Calculate the average price and PnL for each stock
            3. Update the trade positions DataFrame
        '''
        for stock in self.trade_records['stock'].unique():
            stock_trades = self.trade_records.loc[self.trade_records['stock'] == stock]
            stock_trades = stock_trades.loc[stock_trades['status'] == 'Filled']

            # calculate the total quantity given Buy and Sell signal types
            buy_quantity = stock_trades.loc[stock_trades['signal_type'] == 'Buy', 'quantity'].sum()
            sell_quantity = stock_trades.loc[stock_trades['signal_type'] == 'Sell', 'quantity'].sum()

            total_quantity = buy_quantity - sell_quantity
            # take in current price
            value = total_quantity * close_price.iloc[-1]

            new_trade_position = pd.DataFrame(
                {"date": current_datetime, 'stock': stock, 'quantity': total_quantity, 'value': value}, index=[0])
            self.trade_positions = pd.concat([self.trade_positions, new_trade_position], ignore_index=True)

        return

    def backtest(self):

        '''
        Backtest the trade order
        Logic:
            1. Loop through each day in the price data
            2. Check if any existing trades has hit the stop loss, take profit or trailing stop
            3. Check if there are any new trades to be executed
        '''
        days_with_orders = self.trade_order.date.unique().tolist()
        for index, row in self.ohlc.iterrows():
            if row['Date'] in days_with_orders:
                trade_details = self.trade_order.loc[self.trade_order['date'] == row['Date']].squeeze()
                stock = trade_details['stock']
                date = trade_details['date']
                quantity = trade_details['quantity']
                price = trade_details['price']
                signal_type = trade_details['signal_type']
                order_type = trade_details['order_type']
                stop_loss = trade_details['stop_loss']
                take_profit = trade_details['take_profit']
                trailing_stop = trade_details['trailing_stop']
                duration = trade_details['duration']

                if signal_type == 'Buy':
                    self.buy(
                        stock=stock,
                        date=date,
                        quantity=quantity,
                        price=price,
                        close_price=self.ohlc['Close'].loc[index],
                        high_price=self.ohlc['High'].loc[index],
                        low_price=self.ohlc['Low'].loc[index],
                        duration=duration
                    )
                elif signal_type == 'Sell':
                    self.sell(
                        stock=stock,
                        date=date,
                        quantity=quantity,
                        price=price,
                        close_price=self.ohlc['Close'].loc[index],
                        high_price=self.ohlc['High'].loc[index],
                        low_price=self.ohlc['Low'].loc[index],
                        duration=duration
                    )

            print('Updating Trade Positions', index)
            self.update_trade_positions(
                current_datetime=row['Date'],
                close_price=self.ohlc['Close']
            )
