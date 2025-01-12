import datetime
import pandas as pd

import backtrader as bt
from backtrader.feed import DataBase
import qmtstore

from xtquant import xtdata

def on_data_update(datas):
    for stock_code in datas:
        print(stock_code, datas[stock_code])

def on_data_update(data):
    """数据更新回调函数"""
    # data是本次触发的数据(单条)
    code_list = list(data.keys())

    # 在回调中获取完整K线数据
    klines = xtdata.get_market_data_ex(
        field_list=["time", "open", "high", "low", "close", "volume"],
        stock_list=code_list,
        start_time="20241213",
        period="1m"
    )
    print("\n数据更新:")
    print(klines)

class MetaQMTData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTData, cls).__init__(name, bases, dct)

        # Register with the store
        qmtstore.QMTStore.DataCls = cls

class QMTData(DataBase, metaclass=MetaQMTData):
    _store = qmtstore.QMTStore
    def __init__(self, **kwargs):
        super(QMTData, self).__init__()
        self.qmt = self._store(**kwargs)
        xtdata.enable_hello = False
        print("QMTData init")

    def setenvironment(self, env):
        '''Receives an environment (cerebro) and passes it over to the store it
        belongs to'''
        super(QMTData, self).setenvironment(env)
        env.addstore(self.qmt)

    def start(self):
        '''Starts the QMT connecction and gets the real contract and
        contractdetails if it exists'''
        super(QMTData, self).start()
        self.qlive = self.qmt.start(data=self)

    def stop(self):
        '''Stops and tells the store to stop'''
        super(QMTData, self).stop()
        #self.qmt.stop()

    def convert_qmt2bt_data(self, data=None):
        """
        将 QMT 数据格式转换为 Backtrader 数据格式。
        
        :param datas: dict, 包含时间、开盘价、收盘价、最高价、最低价、成交量等数据
        :return: pandas.DataFrame 转换后的数据格式
        """
        # 检查入参是否为空
        if data is None:
            return None  # 如果数据为空，直接返回 None

        # 转换为目标格式
        dates = data['time'].columns  # 提取日期列
        symbol = list(data['time'].index)[0]  # 提取股票代码

        # 构建目标 DataFrame
        converted_data = pd.DataFrame({
            'date': pd.to_datetime(dates, format='%Y%m%d'),
            'open': data['open'].loc[symbol].values,
            'close': data['close'].loc[symbol].values,
            'high': data['high'].loc[symbol].values,
            'low': data['low'].loc[symbol].values,
            'volume': data['volume'].loc[symbol].values,
        })

        # 设置日期为索引，添加格式化列
        converted_data['date'] = converted_data['date'].dt.date
        converted_data.set_index('date', inplace=True)

        # 输出结果
        #print("平安银行日线数据:")
        #print(converted_data)
        return converted_data

    def history_data(self, stock="000001.SZ", period="1d", start="20240101", end="20250101"):
        # 1.下载数据
        xtdata.download_history_data(
            stock_code=stock,
            period=period,
            start_time=start,
            end_time=end
        )

        # 2.查询数据
        data = xtdata.get_market_data(
            field_list=['time','open','close','high','low','volume'],  # 需要的字段
            stock_list=[stock],  # 股票代码
            period=period,            # 日线数据
            start_time=start,  # 起始日期
            end_time=end     # 结束日期
        )

        hisdata = self.convert_qmt2bt_data(data)
        return hisdata


    def subscribe_live_data(self, stock="000001.SZ", period="1m", start="20240101", end="20250101"):
        seq = xtdata.subscribe_quote(stock_code=stock, period=period, count=-1, callback=on_data_update)
        print("开始接收实时数据...")
        print(seq)
        try:
            xtdata.run()
        except KeyboardInterrupt:
            print("程序结束")
        return seq

    def unsubscribe_live_data(self, seq=None):
        # 检查入参是否为空
        if seq is None:
            return None  # 如果数据为空，直接返回 None
        xtdata.unsubscribe_quote(seq)