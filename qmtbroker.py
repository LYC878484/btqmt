from backtrader import BrokerBase, OrderBase
from qmtstore import QMTStore
from xtquant import xtconstant
import backtrader as bt
import queue

class QMTOrder(OrderBase):
    def __init__(self, action, **kwargs):
        # ✅ 关键步骤：设置 ordtype
        self.ordtype = self.Buy if action == 'BUY' else self.Sell
        super(QMTOrder, self).__init__()

        self.action = action  # 自己定义的字段

    def __str__(self):
        return (f"QMTOrder({self.ref}) - Action: {self.action}, Size: {self.size}, "
                f"Price: {self.price}, ExecType: {self.exectype}")

class MetaQMTBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTBroker, cls).__init__(name, bases, dct)
        QMTStore.BrokerCls = cls

class QMTBroker(BrokerBase, metaclass=MetaQMTBroker):
    def __init__(self, **kwargs):
        super(QMTBroker, self).__init__()
        self.qmtstore = QMTStore(**kwargs)
        self.startingcash = self.cash = self.getcash()
        self.startingvalue = self.value = self.getvalue()
        self._notifs = queue.Queue()
        self.orders = {}
        print("QMTBroker init")

    def getcash(self):
        # print("query cash:")
        asset = self.qmtstore.xt_trader.query_stock_asset(self.qmtstore.account)
        # if asset:
        #     print("cash {0}".format(asset.cash))

        # This call cannot block if no answer is available from ib
        self.cash = asset.cash
        return self.cash

    def getvalue(self, datas=None):
        # print("query total_asset:")
        asset = self.qmtstore.xt_trader.query_stock_asset(self.qmtstore.account)
        # if asset:
        #     print("total_asset {0}".format(asset.total_asset))

        self.value = asset.total_asset
        return self.value

    def notify(self, order):
        self._notifs.put(order.clone())
        
    def get_notification(self):
        try:
            return self._notifs.get(False)
        except queue.Empty:
            return None

    # === 委托下单 ===
    def makeorder(self, owner, data, size, action, price, exectype, **kwargs):
        # 构建 QMTOrder 实例
        order = QMTOrder(action, owner=owner, data=data, size=size, price=price, exectype=exectype, **kwargs)
        return order

    def submit(self, order):
        order.submit(self)
        stock_code = order.data._dataname  # 假设 data._dataname 是股票代码
        # QMT 的操作方向
        action = xtconstant.STOCK_BUY if order.isbuy else xtconstant.STOCK_SELL
        volume = order.size
        # 默认限价单
        price_type = xtconstant.FIX_PRICE
        price = order.price
        print(f"submit stock_code{stock_code} action{action} volume{volume} price_type{price_type} price{price}")
        # 调用 QMT 下单接口
        order_id = self.qmtstore.place_order(stock_code, action, abs(volume), price, price_type)
        order.qmt_order_id = order_id

        print(f"✅ 提交订单: {order}")
        return order

    def cancel(self, order):
        # 如果订单已经取消或已完成，跳过
        if order.status in [bt.Order.Cancelled, bt.Order.Completed, bt.Order.Expired]:
            print(f"❎ 订单 {order.ref} 已完成/取消，无法重复取消")
            return
        qmt_order_id = getattr(order, 'qmt_order_id', None)
        if qmt_order_id is None:
            print(f"❌ 找不到订单 {order.ref} 对应的 QMT 委托编号，无法取消")
            return

        return self.qmtstore.cancel_order(qmt_order_id)

    def buy(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            **kwargs):
        print(f"qmtbroker buy size {size} price {price} exectype {exectype}")
        # 构建order
        order = self.makeorder(owner, data, size, 'BUY', price, exectype, **kwargs)
        # 提交订单
        self.submit(order)
        return order


    def sell(self, owner, data, size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0, oco=None,
            trailamount=None, trailpercent=None,
            **kwargs):
        print(f"qmtbroker sell size {size} price {price} exectype {exectype}")
        # 构建order
        order = self.makeorder(owner, data, size, 'SELL', price, exectype, **kwargs)
        # 提交订单
        self.submit(order)
        return order


