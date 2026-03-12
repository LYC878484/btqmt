import queue

import backtrader as bt
from backtrader import BrokerBase, OrderBase
from xtquant import xtconstant

from qmtstore import QMTStore


ACCEPTED = {xtconstant.ORDER_REPORTED}
PARTIAL = {xtconstant.ORDER_PARTSUCC_CANCEL, xtconstant.ORDER_PART_SUCC}
COMPLETED = {xtconstant.ORDER_SUCCEEDED}
CANCELED = {xtconstant.ORDER_PART_CANCEL, xtconstant.ORDER_CANCELED}
REJECTED = {xtconstant.ORDER_JUNK}
IGNORED = {
    xtconstant.ORDER_UNREPORTED,
    xtconstant.ORDER_WAIT_REPORTING,
    xtconstant.ORDER_REPORTED_CANCEL,
    xtconstant.ORDER_UNKNOWN,
}


class QMTOrderStateManager:
    def __init__(self):
        self._orders = {}  # qmt_order_id -> bt.Order

    def register(self, qmt_order_id, bt_order):
        self._orders[qmt_order_id] = bt_order

    def handle_trade(self, trade):
        order_id = getattr(trade, "order_id", None) or getattr(trade, "order_sysid", None)
        order = self._orders.get(order_id)
        if order is None:
            return None

        price = (
            getattr(trade, "price", None)
            or getattr(trade, "trade_price", None)
            or getattr(trade, "match_price", None)
        )
        size = (
            getattr(trade, "volume", None)
            or getattr(trade, "qty", None)
            or getattr(trade, "quantity", None)
            or getattr(trade, "match_qty", None)
        )
        if price is None or size is None:
            return order

        comm = getattr(trade, "commission", None) or getattr(trade, "fee", 0) or 0

        # accumulate execution info
        order.executed.size += size
        order.executed.price = price  # last price; BT will keep latest
        order.executed.value += price * size
        order.executed.comm += comm
        return order

    def handle_cancel_error(self, cancel_error):
        order_id = getattr(cancel_error, "order_id", None) or getattr(cancel_error, "order_sysid", None)
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.addinfo(cancel_error=getattr(cancel_error, "error_id", None))
        return order

    def handle_order_error(self, order_error):
        order_id = getattr(order_error, "order_id", None) or getattr(order_error, "order_sysid", None)
        order = self._orders.get(order_id)
        if order is None:
            return None
        order.reject()
        self._finalize(order_id)
        return order

    def handle_order(self, qmt_order):
        order = self._orders.get(qmt_order.order_id)
        if order is None:
            return None

        status = qmt_order.order_status

        if status in ACCEPTED:
            order.accept()
        elif status in PARTIAL:
            order.partial()
        elif status in COMPLETED:
            order.completed()
            self._finalize(qmt_order.order_id)
        elif status in CANCELED:
            order.cancel()
            self._finalize(qmt_order.order_id)
        elif status in REJECTED:
            order.reject()
            self._finalize(qmt_order.order_id)
        elif status in IGNORED:
            return None

        return order

    def _finalize(self, qmt_order_id):
        self._orders.pop(qmt_order_id, None)


class QMTOrder(OrderBase):
    def __init__(self, action, **kwargs):
        super(QMTOrder, self).__init__(**kwargs)
        self.ordtype = self.Buy if action == "BUY" else self.Sell
        self.action = action


class MetaQMTBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        super(MetaQMTBroker, cls).__init__(name, bases, dct)
        QMTStore.BrokerCls = cls


class QMTBroker(BrokerBase, metaclass=MetaQMTBroker):
    def __init__(self, **kwargs):
        super(QMTBroker, self).__init__()
        self.qmtstore = QMTStore(**kwargs)
        self.order_state_mgr = QMTOrderStateManager()

        self.notifs = queue.Queue()
        self.orders = {}
        self.cash = 0.0
        self.value = 0.0

    def getcash(self):
        asset = self.qmtstore.query_asset()
        self.cash = asset.cash
        return self.cash

    def getvalue(self, datas=None):
        asset = self.qmtstore.query_asset()
        self.value = asset.total_asset
        return self.value

    def notify(self, order):
        self.notifs.put(order.clone())

    def get_notification(self):
        self._drain_store_events()
        try:
            return self.notifs.get(False)
        except queue.Empty:
            return None

    def _drain_store_events(self):
        while True:
            try:
                qmt_order = self.qmtstore.order_events.get_nowait()
            except queue.Empty:
                break
            bt_order = self.order_state_mgr.handle_order(qmt_order)
            if bt_order is not None:
                self.notify(bt_order)

        while True:
            try:
                trade = self.qmtstore.trade_events.get_nowait()
            except queue.Empty:
                break
            bt_order = self.order_state_mgr.handle_trade(trade)
            if bt_order is not None:
                self.notify(bt_order)

        while True:
            try:
                cancel_error = self.qmtstore.cancel_error_events.get_nowait()
            except queue.Empty:
                break
            bt_order = self.order_state_mgr.handle_cancel_error(cancel_error)
            if bt_order is not None:
                self.notify(bt_order)

        while True:
            try:
                order_error = self.qmtstore.order_error_events.get_nowait()
            except queue.Empty:
                break
            bt_order = self.order_state_mgr.handle_order_error(order_error)
            if bt_order is not None:
                self.notify(bt_order)

    def makeorder(self, owner, data, size, action, price, exectype, **kwargs):
        return QMTOrder(
            action,
            owner=owner,
            data=data,
            size=size,
            price=price,
            exectype=exectype,
            **kwargs
        )

    def submit(self, order):
        order.submit(self)
        self.notify(order)  # Submitted

        stock_code = order.data._dataname
        action = xtconstant.STOCK_BUY if order.isbuy() else xtconstant.STOCK_SELL
        volume = abs(int(order.size))
        price = order.price
        price_type = xtconstant.FIX_PRICE

        qmt_order_id = self.qmtstore.place_order(
            stock_code, action, volume, price, price_type
        )
        if qmt_order_id is None or qmt_order_id < 0:
            order.reject()
            self.notify(order)
            return order

        order.qmt_order_id = qmt_order_id
        self.orders[qmt_order_id] = order
        self.order_state_mgr.register(qmt_order_id, order)
        return order

    def cancel(self, order):
        if order.status in [bt.Order.Canceled, bt.Order.Completed, bt.Order.Expired]:
            return None

        qmt_order_id = getattr(order, "qmt_order_id", None)
        if qmt_order_id is None:
            return None

        return self.qmtstore.cancel_order(qmt_order_id)

    def buy(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        **kwargs):
        order = self.makeorder(owner, data, size, "BUY", price, exectype, **kwargs)
        return self.submit(order)

    def sell(
        self,
        owner,
        data,
        size,
        price=None,
        plimit=None,
        exectype=None,
        valid=None,
        tradeid=0,
        oco=None,
        trailamount=None,
        trailpercent=None,
        **kwargs
    ):
        order = self.makeorder(owner, data, size, "SELL", price, exectype, **kwargs)
        return self.submit(order)
