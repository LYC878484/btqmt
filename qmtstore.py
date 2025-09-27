
import backtrader as bt
from backtrader.metabase import MetaParams
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
import time, datetime

class QMTTraderCallback(XtQuantTraderCallback):
    def on_connected(self):
        """
        连接成功推送
        """
        print(datetime.datetime.now(),'连接成功回调')

    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print(datetime.datetime.now(),'连接断开回调')

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print(f"委托回调: {order.order_remark} 状态: {order.order_status}")


    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print(datetime.datetime.now(), '成交回调', trade.order_remark)


    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        # print("on order_error callback")
        # print(order_error.order_id, order_error.error_id, order_error.error_msg)
        print(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print(f"异步委托回调 {response.order_remark}")

    def on_cancel_order_stock_async_response(self, response):
        """
        收到撤单回调信息
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)

    def on_account_status(self, status):
        """
        账号状态信息变动推送
        :param response: XtAccountStatus 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)


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
    params = (
        ('account_id', '8886991198'),
        ('path', r'D:\国金证券QMT交易端\bin.x64/../userdata_mini'),
    )

    BrokerCls = None  # broker class will autoregister
    DataCls = None  # data class will auto register

    @classmethod
    def getbroker(cls, *args, **kwargs):
        '''Returns broker with *args, **kwargs from registered ``BrokerCls``'''
        if cls.BrokerCls is None:
            raise RuntimeError("BrokerCls is not registered. Make sure QMTBroker is imported.")
        return cls.BrokerCls(*args, **kwargs)

    @classmethod
    def getdata(cls, *args, **kwargs):
        '''Returns ``DataCls`` with args, kwargs'''
        if cls.DataCls is None:
            raise RuntimeError("DataCls is not registered. Make sure QMTData is imported.")
        return cls.DataCls(*args, **kwargs)

    def __init__(self):
        super(QMTStore, self).__init__()
        # 生成session id 整数类型 同时运行的策略不能重复
        self.session_id = int(time.time())
        self.xt_trader = XtQuantTrader(self.p.path, self.session_id)
        # 创建资金账号account_id证券账号对象 股票账号为STOCK 信用CREDIT 期货FUTURE
        self.account = StockAccount(self.p.account_id, 'STOCK')
        # 创建交易回调类对象，并声明接收回调
        self.callback = QMTTraderCallback()
        self.xt_trader.register_callback(self.callback)
        self.connected = False
        self.cash = 0.0
        self.position_dict = {}
        self.position_available_dict = {}
        self._connect_and_subscribe()

    def _connect_and_subscribe(self):
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
        self.update_account_info()

    def update_account_info(self):
        info = self.xt_trader.query_stock_asset(self.account)
        self.cash = info.cash
        print("账户可用资金 (cash):", self.cash)
        positions = self.xt_trader.query_stock_positions(self.account)
        self.position_dict = {pos.stock_code: pos.volume for pos in positions}
        self.position_available_dict = {pos.stock_code : pos.can_use_volume for pos in positions}
        print("📊 当前持仓明细：")
        for pos in positions:
            floating_profit = pos.market_value - pos.can_use_volume * pos.avg_price
            print(
                f"📈 股票: {pos.stock_code}, "
                f"持仓: {pos.volume}, "
                f"可用: {pos.can_use_volume}, "
                f"市值: {pos.market_value:.2f}, "
                f"成本价: {pos.avg_price:.2f}, "
                f"浮盈: {round(floating_profit, 2)}"
            )

    def cancel_order(self, order_id):
        '''Proxy to cancelOrder'''
        if not self.connected:
            raise RuntimeError('QMT尚未连接, 取消订单失败')
        # 使用订单编号撤单
        print("cancel order:")
        # 根据订单编号对委托进行撤单操作(返回是否成功发出撤单指令，0: 成功, -1: 表示撤单失败)
        return self.xt_trader.cancel_order_stock(self.account, order_id)

    def place_order(self, stock_code, action, volume, price, price_type=xtconstant.FIX_PRICE, remark='strategy1'):
        '''Proxy to placeOrder'''
        if not self.connected:
            raise RuntimeError('QMT尚未连接, 下单失败')
        print("order using the fix price:")
        # 使用同步下单返回订单编号(系统生成的订单编号，成功委托后的订单编号为大于0的正整数，如果为-1表示委托失败)
        order_id = self.xt_trader.order_stock(
            self.account, stock_code, action, volume, price_type, price, remark, f"[{datetime.datetime.now().strftime('%H:%M:%S')}]"
        )
        return order_id
    

