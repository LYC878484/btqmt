import backtrader as bt
import qmtstore
import qmtbroker
import qmtdata


class LiveLimitBuy(bt.Strategy):
    params = dict(target_price=1.50, stake=100)

    def log(self, txt):
        dt = self.datas[0].datetime.datetime(0)
        print(f"{dt}, {txt}")

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        print(f"live strategy on {self.data._dataname}")

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
        self.log(f"Close {self.dataclose[0]:.2f}")
        if not self.datas[0].islive():
            return
        if self.order:
            return
        if not self.position and self.dataclose[0] <= self.p.target_price:
            self.log(f"触发买入 size:{self.p.stake} price:{self.p.target_price}")
            self.order = self.buy(size=self.p.stake,
                                  exectype=bt.Order.Limit,
                                  price=self.p.target_price)


def run():
    cerebro = bt.Cerebro()

    # store & broker
    qmt_store = qmtstore.QMTStore()
    qmt_broker = qmtbroker.QMTBroker()
    cerebro.setbroker(qmt_broker)

    # live data feed via miniQMT
    data = qmtdata.QMTData(stock="512730.SH", period="1d")
    cerebro.adddata(data)

    cerebro.addstrategy(LiveLimitBuy, target_price=1.50, stake=100)
    cerebro.run()


if __name__ == "__main__":
    run()
