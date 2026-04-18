'''
Created on 2026-04-18
@author: alex

'''
from price_helper.core import get_closest_price, PriceNotFoundError 
from datetime import datetime
from price_helper import PriceHelper
import os

try:
  # variable specified in debugger launch config
  price_folder = os.environ.get('PRICEFOLDER')
  if price_folder:
    helper = PriceHelper(price_folder)
  else:
    #helper = PriceHelper()
    print('no path provided')
  price = helper.get_closest_price(
      dt=datetime(2024, 1, 15, 12, 30),
      pair="BTC_USDT",
      tolerance_seconds=60  # 1 minute tolerance
  )
  print(price)
  price = helper.get_closest_price(
    dt=datetime(2024, 1, 15, 12, 30),
    pair="BTC_USD",
    tolerance_seconds=60  # 1 minute tolerance
    )
except PriceNotFoundError as e:
    print(f"Price not found: {e}")