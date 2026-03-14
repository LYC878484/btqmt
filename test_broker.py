import backtrader as bt
import akshare as ak
import pandas as pd
from datetime import datetime
import qmtstore
import qmtbroker
import qmtdata
from xtquant import xtconstant

class TestStrategy(bt.Strategy):
    params = dict(target_price=1.50, stake=100)

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()}, {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        print(f"debug buy 股票代码 {self.data._dataname}")

    def notify_order(self, order):
        status = order.getstatusname()
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f"订单提交 ref:{order.ref} status:{status}")
        elif order.status == order.Partial:
            self.log(f"部分成交 ref:{order.ref} size:{order.executed.size} price:{order.executed.price}")
        elif order.status == order.Completed:
            self.log(f"成交完毕 ref:{order.ref} size:{order.executed.size} price:{order.executed.price}")
            self.order = None
        elif order.status in [order.Canceled, order.Rejected, order.Expired]:
            self.log(f"订单结束 ref:{order.ref} status:{status} info:{order.info}")
            self.order = None

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])
        if self.order:
            return
        if not self.position and self.dataclose[0] <= self.p.target_price:
            self.log(f"触发买入 size:{self.p.stake} price:{self.p.target_price}")
            self.order = self.buy(size=self.p.stake,
                                  exectype=bt.Order.Limit,
                                  price=self.p.target_price)

def runstrategy():
    cerebro = bt.Cerebro()

    qmt_store = qmtstore.QMTStore(account_id='8886991198', path=r'D:\国金证券QMT交易端\bin.x64/../userdata_mini')

    # 增加一个策略
    cerebro.addstrategy(TestStrategy)

    # 获取并且处理数据
    stock_zh_a_hist_df = ak.stock_zh_a_hist(
        symbol="000810",
        period="daily",
        start_date="20221001",
        end_date="20241017",
        adjust=""
    ).iloc[:, :7]
    stock_zh_a_hist_df.drop(columns=['股票代码'], inplace=True)
    stock_zh_a_hist_df.columns = ['date', 'open', 'close', 'high', 'low', 'volume']
    stock_zh_a_hist_df['openinterest'] = 0
    stock_zh_a_hist_df.index = pd.to_datetime(stock_zh_a_hist_df['date'])
    # 打印数据调试使用
    # print(stock_zh_a_hist_df)

    # 系统依据akshare获取的数据在所需时间段执行策略
    start_date = datetime(2023, 9, 4)  # 回测开始时间
    end_date = datetime(2024, 9, 16)  # 回测结束时间
    data = bt.feeds.PandasData(dataname=stock_zh_a_hist_df, fromdate=start_date, todate=end_date)  # 加载数据
    data._dataname = '000810.SZ'
    # qmt_data = qmt_store.getdata()
    cerebro.adddata(data)  # 将数据传入回测系统

    qmt_broker = qmt_store.getbroker()
    cerebro.setbroker(qmt_broker)

    cerebro.run()

    # 连接成功后才能下单
    # if qmt_store.connected:
    #     stock_code = '512730.SH'  # 股票代码
    #     action = xtconstant.STOCK_BUY  # xtconstant.STOCK_BUY or xtconstant.SELL
    #     volume = 100  # 下单数量，必须是100的整数倍
    #     price = 1.5  # 限价
    #     order_id = qmt_store.place_order(stock_code, action, volume, price)
    #     print(f"下单成功，订单编号: {order_id}")
    #     cancel_result  = qmt_store.cancel_order(order_id)
    #     if cancel_result == 0:
    #         print(f"撤单成功，订单编号: {order_id}")
    #     elif cancel_result == -1:
    #         print(f"撤单失败，订单编号: {order_id}")
    #     else:
    #         print(f"无效返回值: {order_id}")
    #     orders = qmt_store.xt_trader.query_stock_orders(qmt_store.account)
    #     print("orders:", len(orders))
    #     for order in orders:
    #         print(order.stock_code, order.order_volume, order.price)
    # else:
    #     print("尚未连接 QMT")

if __name__ == '__main__':
    runstrategy()
