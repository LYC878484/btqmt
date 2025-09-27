import backtrader as bt
import akshare as ak
import pandas as pd
from datetime import datetime
import qmtstore
import qmtbroker
import qmtdata
from xtquant import xtconstant

class TestStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close
        self.executed = False
        print(f"test buy 股票代码{self.data._dataname}")
        

    def notify_order(self, order):
        if order.status == order.Completed:
            print('订单成交')

    def next(self):
        # 此处完成实际买卖
        self.log('Close, %.2f' % self.dataclose[0])
        if not self.executed:
            self.buy(size=100, exectype=bt.Order.Limit, price=1.5)
            self.executed = True
        # if self.executed==True
        #     self.cancel(order)

def runstrategy():
    cerebro = bt.Cerebro()

    qmt_store = qmtstore.QMTStore()

    # 增加一个策略
    cerebro.addstrategy(TestStrategy)

    # 获取并且处理数据
    stock_zh_a_hist_df = ak.stock_zh_a_hist(symbol="000810", period="daily", start_date="20221001", end_date='20241017', adjust="").iloc[:, :7]
    del stock_zh_a_hist_df['股票代码']
    # 处理字段命名，以符合 Backtrader 的要求
    stock_zh_a_hist_df.columns = [
        'date',
        'open',
        'close',
        'high',
        'low',
        'volume',
    ]
    # 把 date 作为日期索引，以符合 Backtrader 的要求
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
'''
    stock_zh_a_hist_df = qmtdata
    data = bt.feeds.PandasData(dataname=stock_zh_a_hist_df, fromdate=start_date, todate=end_date)
'''