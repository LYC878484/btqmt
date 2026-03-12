import datetime
import time

from backtrader.metabase import MetaParams
from backtrader.utils.py3 import queue
from xtquant import xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount


class QMTTraderCallback(XtQuantTraderCallback):
    def __init__(self, store):
        self.store = store

    def on_connected(self):
        self.store.connected = True
        self.store.put_notification("connection", "connected")

    def on_disconnected(self):
        self.store.connected = False
        self.store.put_notification("connection", "disconnected")

    def on_stock_order(self, order):
        self.store.put_notification("order", order)
        self.store.order_events.put(order)

    def on_stock_trade(self, trade):
        self.store.put_notification("trade", trade)
        self.store.trade_events.put(trade)

    def on_order_error(self, order_error):
        self.store.put_notification("order_error", order_error)
        self.store.order_error_events.put(order_error)

    def on_cancel_error(self, cancel_error):
        self.store.put_notification("cancel_error", cancel_error)
        self.store.cancel_error_events.put(cancel_error)


class MetaSingleton(MetaParams):
    def __init__(cls, name, bases, dct):
        super(MetaSingleton, cls).__init__(name, bases, dct)
        cls._singleton = None

    def __call__(cls, *args, **kwargs):
        if cls._singleton is None:
            cls._singleton = super(MetaSingleton, cls).__call__(*args, **kwargs)
        return cls._singleton


class QMTStore(metaclass=MetaSingleton):
    params = (
        ("account_id", "xxxx"),
        ("account_type", "STOCK"),
        ("path", r"D:\国金证券QMT交易端\bin.x64/../userdata_mini"),
    )

    BrokerCls = None
    DataCls = None

    @classmethod
    def getbroker(cls, *args, **kwargs):
        if cls.BrokerCls is None:
            raise RuntimeError("BrokerCls is not registered. Import qmtbroker first.")
        return cls.BrokerCls(*args, **kwargs)

    @classmethod
    def getdata(cls, *args, **kwargs):
        if cls.DataCls is None:
            raise RuntimeError("DataCls is not registered. Import qmtdata first.")
        return cls.DataCls(*args, **kwargs)

    def __init__(self):
        super(QMTStore, self).__init__()
        self.notifs = queue.Queue()
        self.broker = None
        self.connected = False
        self.order_events = queue.Queue()
        self.trade_events = queue.Queue()
        self.cancel_error_events = queue.Queue()
        self.order_error_events = queue.Queue()

        self.session_id = int(time.time())
        self.xt_trader = XtQuantTrader(self.p.path, self.session_id)
        self.account = StockAccount(self.p.account_id, self.p.account_type)
        self.callback = QMTTraderCallback(self)
        self.xt_trader.register_callback(self.callback)
        self.connect_and_subscribe()

    def put_notification(self, msg, *args, **kwargs):
        self.notifs.put((msg, args, kwargs))

    def get_notifications(self):
        self.notifs.put(None)
        items = []
        while True:
            item = self.notifs.get()
            if item is None:
                break
            items.append(item)
        return items

    def connect_and_subscribe(self):
        self.xt_trader.start()

        connect_result = self.xt_trader.connect()
        if connect_result == 0:
            print('建立交易连接...已成功')
        else:
            raise Exception(f'QMT连接失败,返回码 {connect_result}')

        subscribe_result = self.xt_trader.subscribe(self.account)
        if subscribe_result == 0:
            print('订阅交易回调...已成功')
        else:
            raise Exception(f'QMT订阅失败,返回码 {subscribe_result}')

        self.connected = True
        self.put_notification("connection", "ready")

    def cancel_order(self, order_id):
        if not self.connected:
            raise RuntimeError("QMT is not connected")
        return self.xt_trader.cancel_order_stock(self.account, order_id)

    def place_order(
        self,
        stock_code,
        action,
        volume,
        price,
        price_type=xtconstant.FIX_PRICE,
        remark="strategy"):
        if not self.connected:
            raise RuntimeError("QMT is not connected")

        tag = "[{}]".format(datetime.datetime.now().strftime("%H:%M:%S"))
        order_id = self.xt_trader.order_stock(
            self.account, stock_code, action, volume, price_type, price, remark, tag
        )

        return order_id


    def query_asset(self):
        return self.xt_trader.query_stock_asset(self.account)

    def query_positions(self):
        return self.xt_trader.query_stock_positions(self.account)
