import numpy as np


def calculate_ibkr_fixed_cost(qty, price_per_share):
    cost_per_share = 0.005
    fixed_cost = qty * cost_per_share

    if fixed_cost < 1:
        fixed_cost = 1

    if fixed_cost > price_per_share * qty * 0.01:
        fixed_cost = price_per_share * qty * 0.01

    # Regulatory Fees
    sec_transaction_fee = 0.0000278 * fixed_cost
    finra_trading_activity_fee = 0.000166 * qty

    return fixed_cost + sec_transaction_fee + finra_trading_activity_fee


# TODO: future works to identify the exchange and
# def calculate_ibkr_tiered_cost(current_month_vol, qty, price):
#     price_dict = {
#         300000: 0.0035,
#         3000000: 0.002,
#         20000000: 0.0015,
#         100000000: 0.001,
#         np.inf: 0.0005,
#     }
#
#     cost = 0
#     remaining_qty = qty
#     while remaining_qty > 0:
#         for key in price_dict:
#             if current_month_vol < key:
#                 cost_per_share = price_dict[key]
#                 if current_month_vol + remaining_qty <= key:
#                     cost += remaining_qty * cost_per_share
#                     remaining_qty = 0
#                     break
#                 else:
#                     remaining_vol_in_tier = key - current_month_vol
#                     remaining_qty -= remaining_vol_in_tier
#                     cost += remaining_vol_in_tier * cost_per_share
#                     current_month_vol += remaining_vol_in_tier
#                     break
#
#     # Regulatory Fees
#     sec_transaction_fee = 0.0000278 * cost
#     finra_trading_activity_fee = 0.000166 * qty
#
#     # Exchange Fees
#
#     # Clearing Fees
#     clearing_fees = 0.00020 * qty
#
#     # Pass Through Fees
#     nyse_pass_through_fees = cost * 0.000175
#     finra_pass_through_fees = max(cost * 0.00056, 8.30)
#
#     # TODO: check if we are actly using tiered pricing as exchange need to be added
#
#     if cost < 0.35:
#         cost = 0.35
#
#     if cost > price * qty * 0.01:
#         cost = price * qty * 0.01
#
#     return cost
