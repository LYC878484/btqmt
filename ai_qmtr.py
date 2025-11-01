import backtrader as bt
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import threading
import queue
import datetime
import time


class QMTStore(bt.Store):
    params = (
        ('account_id', 'xxxxxx'),
        ('path', r'D:\国金证券QMT交易端\bin.x64/../userdata_mini'),
    )

    def __init__(self):
        self.session_id = int(time.time())
        self.xt_trader = XtQuantTrader(self.p.path, self.session_id)
        self.account = StockAccount(self.p.account_id, 'STOCK')
        self.callback = QMTTraderCallback(self)
        self.xt_trader.register_callback(self.callback)
        self.order_queue = queue.Queue()   # 用于异步订单事件
        self.tick_queue = queue.Queue()    # 用于异步tick行情事件
        self.position_dict = {}
        self.cash = 0.0
        self.connected = False
        self._connect_and_subscribe()

    def _connect_and_subscribe(self):
        self.xt_trader.start()
        ret = self.xt_trader.connect()
        if ret != 0:
            raise Exception(f'QMT连接失败，返回码 {ret}')
        ret = self.xt_trader.subscribe(self.account)
        if ret != 0:
            raise Exception(f'QMT订阅失败，返回码 {ret}')
        self.connected = True
        self.update_account_info()

    def update_account_info(self):
        info = self.xt_trader.query_stock_asset(self.account)
        self.cash = info.m_dCash
        positions = self.xt_trader.query_stock_positions(self.account)
        self.position_dict = {pos.stock_code: pos.m_nVolume for pos in positions}

    def getbroker(self):
        if not hasattr(self, '_broker'):
            self._broker = QMTBroker(self)
        return self._broker

    def getdata(self, dataname, **kwargs):
        return QMTData(dataname, self, **kwargs)

    def place_order(self, stock_code, action, volume, price, price_type=xtconstant.FIX_PRICE, remark='bt_order'):
        if not self.connected:
            raise RuntimeError('QMT尚未连接')
        async_seq = self.xt_trader.order_stock_async(
            self.account, stock_code, action, volume, price_type, price, remark, stock_code
        )
        return async_seq

    def cancel_order(self, async_seq):
        return self.xt_trader.cancel_order_stock_async(async_seq)


class QMTTraderCallback(XtQuantTraderCallback):
    def __init__(self, store):
        super().__init__()
        self.store = store

    # 订单委托回调
    def on_stock_order(self, order):
        print(f"委托回调: {order.order_remark} 状态: {order.order_status}")
        self.store.order_queue.put(('order', order))

    # 成交回调
    def on_stock_trade(self, trade):
        print(f"成交回调: {trade.order_remark} 价格: {trade.traded_price} 数量: {trade.traded_volume}")
        self.store.order_queue.put(('trade', trade))

    # 委托失败回调
    def on_order_error(self, order_error):
        print(f"委托错误: {order_error.order_remark} 错误信息: {order_error.error_msg}")
        self.store.order_queue.put(('order_error', order_error))

    # 实时tick行情回调（示意用）
    def on_tick(self, tick_data):
        # 假设xt_trader支持此类实时tick回调接口
        self.store.tick_queue.put(tick_data)


class QMTBroker(bt.BrokerBase):
    def __init__(self, store):
        self.store = store
        self.cash = store.cash
        self.positions = store.position_dict.copy()
        self.orders = {}
        self._lock = threading.Lock()
        self._start_callback_thread()

    def _start_callback_thread(self):
        def _worker():
            while True:
                try:
                    item = self.store.order_queue.get(timeout=1)
                except queue.Empty:
                    continue
                if item is None:
                    break
                evt_type, obj = item
                if evt_type == 'order':
                    self._handle_order(obj)
                elif evt_type == 'trade':
                    self._handle_trade(obj)
                elif evt_type == 'order_error':
                    self._handle_order_error(obj)
                self.store.order_queue.task_done()

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_order(self, order):
        async_seq = order.order_id  # 这里假设order_id是下单唯一标识
        with self._lock:
            bt_order = self.orders.get(async_seq, None)
            if bt_order:
                # 根据order.order_status更新bt_order状态
                # 示例：status 0新单，1部分成交，2完全成交，3撤单，4失败等
                if order.order_status == 0:
                    bt_order.status = bt.Order.Submitted
                elif order.order_status == 1:
                    bt_order.status = bt.Order.Partial
                elif order.order_status == 2:
                    bt_order.status = bt.Order.Completed
                elif order.order_status == 3:
                    bt_order.status = bt.Order.Canceled
                elif order.order_status == 4:
                    bt_order.status = bt.Order.Rejected
                bt_order.notify()
                print(f"订单 {async_seq} 状态更新为 {bt_order.getstatusname()}")

    def _handle_trade(self, trade):
        async_seq = trade.order_id
        with self._lock:
            bt_order = self.orders.get(async_seq, None)
            if bt_order:
                # 触发策略成交回报通知
                bt_order.notify()
                print(f"订单 {async_seq} 成交通知")

    def _handle_order_error(self, order_error):
        async_seq = order_error.order_id
        with self._lock:
            bt_order = self.orders.get(async_seq, None)
            if bt_order:
                bt_order.status = bt.Order.Rejected
                bt_order.notify()
                print(f"订单 {async_seq} 错误通知")

    def getcash(self):
        self.cash = self.store.cash
        return self.cash

    def getposition(self, data):
        sym = data._name
        return self.store.position_dict.get(sym, 0)

    def submit_order(self, data, order):
        action = xtconstant.STOCK_BUY if order.isbuy() else xtconstant.STOCK_SELL
        price = order.price if order.price else 0
        volume = int(order.size)
        async_seq = self.store.place_order(data._name, action, volume, price)
        with self._lock:
            self.orders[async_seq] = order
            order.addinfo(async_seq=async_seq)
        return async_seq

    def cancel(self, order):
        async_seq = order.info.get('async_seq', None)
        if async_seq is None:
            return False
        return self.store.cancel_order(async_seq)


class QMTData(bt.DataBase):
    def __init__(self, dataname, store, **kwargs):
        super().__init__()
        self._dataname = dataname
        self.store = store

        # 历史数据加载
        self.history_data = xtdata.get_stock_kline(self._dataname, 'day', 365)
        self._idx = 0

        # 启动实时行情推送线程
        self._tick_data = None
        self._tick_thread = threading.Thread(target=self._tick_pusher, daemon=True)
        self._tick_thread.start()

    def _load(self):
        # 读取历史数据，返回下一条Bar字典
        if self._idx >= len(self.history_data):
            return None
        row = self.history_data.iloc[self._idx]
        self._idx += 1
        dt = datetime.datetime.strptime(row['date'], '%Y-%m-%d')
        return dict(
            datetime=dt,
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            volume=row['volume'],
            openinterest=0,
        )

    def _tick_pusher(self):
        """
        实时行情线程
        订阅并接收tick数据，转换为Backtrader需要的格式，调用 self.put()推送
        """
        # 订阅行情（假设xtdata提供订阅接口）
        def tick_callback(tick):
            # tick结构假设有字段：lastPrice, lastVolume, dateTime, high, low, open, close
            self._tick_data = tick

        # 假设xtdata支持订阅
        xtdata.subscribe_ticks([self._dataname], tick_callback)

        while True:
            if self._tick_data:
                tick = self._tick_data
                dt = datetime.datetime.strptime(tick['dateTime'], '%Y-%m-%d %H:%M:%S.%f')
                bar = dict(
                    datetime=dt,
                    open=tick['open'],
                    high=tick['high'],
                    low=tick['low'],
                    close=tick['lastPrice'],
                    volume=tick['lastVolume'],
                    openinterest=0,
                )
                self.put(**bar)
                self._tick_data = None
            time.sleep(0.1)

