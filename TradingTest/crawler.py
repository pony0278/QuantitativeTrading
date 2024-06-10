import pandas as pd
import math
import os.path
import time
from binance.client import Client
from datetime import timedelta, datetime, timezone
from dateutil import parser
from tqdm import tqdm_notebook  # (Optional, used for progress-bars)

import json
import requests
import pandas as pd

### CONSTANTS
binsizes = {"1m": 1, "5m": 5, '15m': 15, '30m': 30, "1h": 60, '2h': 120, "4h": 240, "1d": 1440}
batch_size = 750


### FUNCTIONS

def minutes_of_new_data(symbol, kline_size, data, source, client):
    """Process old and new histrical price data format through binance api.

    The boundary between new data and old data is 2017.1.1.

    Args:
      symbol (str): Trading pair (ex: BTCUSDT).
      kline_size (str): A frequency of the price data (ex: "1m", "5m",'15m', '30m', "1h", '2h', "4h", "1d")
      data (dataframe): The data from get_all_binance() crawlers.
      source (str): data source (ex:'binance','bitmex')
      client (Binance.Client) (optional): Binance Client object.

    Returns:
      old: OHLCV DataFrame of old format.
      new: OHLCV DataFrame of new format.
    """
    if len(data) > 0:
        old = parser.parse(data["timestamp"].iloc[-1])
    elif source == "binance":
        old = datetime.strptime('1 Jan 2017', '%d %b %Y')
    elif source == "bitmex":
        old = client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=False).result()[0][0][
            'timestamp']
    if source == "binance": new = pd.to_datetime(client.get_klines(symbol=symbol, interval=kline_size)[-1][0],
                                                 unit='ms')
    if source == "bitmex": new = \
    client.Trade.Trade_getBucketed(symbol=symbol, binSize=kline_size, count=1, reverse=True).result()[0][0]['timestamp']
    return old, new + timedelta(minutes=1)


def get_all_binance(symbol, kline_size, save=True, client=Client()):
    """Getting histrical price data through binance api.

    Original code from: https://medium.com/swlh/retrieving-full-historical-data-for-every-cryptocurrency-on-binance-bitmex-using-the-python-apis-27b47fd8137f

    Args:
      symbol (str): Trading pair (ex: BTCUSDT).
      kline_size (str): A frequency of the price data (ex: "1m", "5m",'15m', '30m', "1h", '2h', "4h", "1d")
      save (bool): Save the results in ./history/ to improve the retreive waiting time.
      client (Binance.Client) (optional): Binance Client object.

    Returns:
      pd.DataFrame: OHLCV data for all

    """

    filename = 'history/%s-%s-data.csv' % (symbol, kline_size)
    if os.path.isfile(filename):
        data_df = pd.read_csv(filename)
    else:
        data_df = pd.DataFrame()
    oldest_point, newest_point = minutes_of_new_data(symbol, kline_size, data_df, source="binance", client=client)
    oldest_point = oldest_point.replace(tzinfo=None)
    newest_point = newest_point.replace(tzinfo=None)
    delta_min = (newest_point - oldest_point).total_seconds() / 60
    available_data = math.ceil(delta_min / binsizes[kline_size])
    if oldest_point == datetime.strptime('1 Jan 2017', '%d %b %Y'):
        print('Downloading all available %s data for %s. Be patient..!' % (kline_size, symbol))
    else:
        print('Downloading %d minutes of new data available for %s, i.e. %d instances of %s data.' % (
        delta_min, symbol, available_data, kline_size))
    klines = client.get_historical_klines(symbol, kline_size, oldest_point.strftime("%d %b %Y %H:%M:%S"),
                                          newest_point.strftime("%d %b %Y %H:%M:%S"))
    data = pd.DataFrame(klines,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av',
                                 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert('Asia/Taipei')
    if len(data_df) > 0:
        temp_df = pd.DataFrame(data)
        data_df = pd.concat([data_df, temp_df])
    else:
        data_df = data
    data_df.set_index('timestamp', inplace=True)
    data_df = data_df[~data_df.index.duplicated(keep='last')]
    if save and os.path.exists('./history'): data_df.to_csv(filename)
    print('All caught up..!')
    data_df.index = pd.to_datetime(data_df.index, utc=True)
    data_df = data_df[~data_df.index.duplicated(keep='last')]
    return data_df.astype(float)


def get_nbars_binance(symbol, interval, nbars, client=Client()):
    """Getting histrical price data through binance api by interval arg.

    Args:
      symbol (str): Trading pair (ex: BTCUSDT).
      interval (str): A frequency of the price data (ex: "1m", "5m",'15m', '30m', "1h", '2h', "4h", "1d")
      nbars (int): The number of row data
      client (Binance.Client) (optional): Binance Client object.

    Returns:
        pd.DataFrame: OHLCV data for all

    """
    interval_to_seconds = lambda interval: int(interval[:-1]) * {'m': 60, 'h': 60 * 60, 'd': 60 * 60 * 24}[interval[-1]]

    # calculate crawl time interval
    now = datetime.now(tz=timezone.utc)
    crawl_period = timedelta(seconds=interval_to_seconds(interval) * nbars) + timedelta(days=1)
    test_time = (now - crawl_period).strftime('%d %b %Y')

    # download results
    klines = client.get_historical_klines(symbol, interval, start_str=test_time)
    data = pd.DataFrame(klines,
                        columns=['timestamp', 'open', 'high', 'low', 'close',
                                 'volume', 'close_time', 'quote_av', 'trades',
                                 'tb_base_av', 'tb_quote_av', 'ignore'], dtype=float)
    data.index = pd.to_datetime(data['timestamp'], unit='ms')
    data.index = data.index.tz_localize(timezone.utc)
    return data





