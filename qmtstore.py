import time, datetime
import collections

import backtrader as bt
from backtrader.metabase import MetaParams
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    pass

class MetaSingleton(MetaParams):
    '''Metaclass to make a metaclassed class a singleton'''
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = (
                super(MetaSingleton, cls).__call__(*args, **kwargs))

        return cls._singleton
class QMTStore(metaclass=MetaSingleton):
    BrokerCls = None  # broker class will autoregister
    DataCls = None  # data class will auto register

    @classmethod
    def getdata(cls, *args, **kwargs):
        '''Returns ``DataCls`` with args, kwargs'''
        return cls.DataCls(*args, **kwargs)

    @classmethod
    def getbroker(cls, *args, **kwargs):
        '''Returns broker with *args, **kwargs from registered ``BrokerCls``'''
        return cls.BrokerCls(*args, **kwargs)

    def __init__(self):
        super(QMTStore, self).__init__()
        # Structures to hold datas requests
        self.qs = collections.OrderedDict()  # key: tickerId -> queues
        self.ts = collections.OrderedDict()  # key: queue -> tickerId

        # 指定客户端所在路径, 券商端指定到 userdata_mini文件夹
        # 注意：如果是连接投研端进行交易，文件目录需要指定到f"{安装目录}\userdata"
        path = r'D:\国金证券QMT交易端\bin.x64/../userdata_mini'
        # 生成session id 整数类型 同时运行的策略不能重复
        session_id = int(time.time())
        self.xt_trader = XtQuantTrader(path, session_id)

        # 启动交易线程
        self.xt_trader.start()

        # 创建资金账号为 800068 的证券账号对象 股票账号为STOCK 信用CREDIT 期货FUTURE
        acc = StockAccount('8886991198', 'STOCK')
        # 建立交易连接，返回0表示连接成功
        connect_result = self.xt_trader.connect()
        print('建立交易连接, 返回0表示连接成功', connect_result)
        # 创建交易回调类对象，并声明接收回调
        callback = MyXtQuantTraderCallback()
        self.xt_trader.register_callback(callback)
        # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
        subscribe_result = self.xt_trader.subscribe(acc)
        print('对交易回调进行订阅, 订阅后可以收到交易主推, 返回0表示订阅成功', subscribe_result)

    def start(self, data=None, broker=None):
        pass

    def stop(self):
        pass

    def put_notification(self, msg, *args, **kwargs):
        pass

    def get_notifications(self):
        pass
