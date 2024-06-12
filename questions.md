
Portfolio value is always NAV (net assst value)

Questions: 
1. Does the buy and sell order need to match? 
E.g. 1 Order: Buy 5 Stock, Sell 5 Stock / Sell 5 Stock, Buy 5 Stock --> Order = Closed
What happens when there is a scenario where we buy 5 stock and sell 10 stock?
Does it become Order 1: Buy 5, Sell 5 : Order Closes & Order 2: Sell 5 : Order Opens?

Or will it become
Order 1: Buy 5 Stock, when TP/SL trigger --> Sell 5 Stock: Order Closed
Order 2: Sell 10 Stock, when TP/SL trigger --> Buy 10 Stock: Order Closed

Proposed Idea: Track each stock by the stock symbol, sum(quantity), and SL/TP/TL


2. Will there be a case where there is different stop loss, take profit, trailing stop 
for the same stock of different orders
-There will be different stop loss/ take profit/ trailing stop for different orders
SL/TP/TL should be price instead of percentage 

3. What frequency will the backtest need to support? Daily
-Daily is sufficient for now. 


4. For the trailing stop loss, how do we determine the price to use to calculate the trailing stop price?
-Use input price to track 
-Need more clarification 


5. How should we calculate remaining capital when we are executing a short? 
Does the capital increase from the short sale? 
Is there a % of the short sale that is held as collateral? No, only for margin 

Short @ $5, but dont add it into the capital (portfolio value)
if price goes > 2.5 need to top up margin  [not needed yet]


6. Should we use the volume of the stocks to determine if the trade can be executed?
- Not at backtesting, determined by strategy


7. Do we need to maintain different average prices for long and short positions? 
Long: AAPL  @ $100, Buy 5, AAPL @ $105, Buy 5, Average Price = $102.5 
Short: AAPL @ $100, Sell 5, AAPL @ $105, Sell 5, Average Price = $102.5
Need to split in the entity class, create new column for direction (long/short)


8. Should we track the actual values for SL/TP/TL in the transactions df 
-Input should be actual values 


9. For price calculation, what dp should we use? 2 d.p.

