import backtrader as bt
import qmtstore
import qmtbroker
import qmtdata

def runstrategy():
    # Create a cerebro
    cerebro = bt.Cerebro()

    qmt_store = qmtstore.QMTStore()
    qmt_broker = qmtbroker.QMTBroker()
    cerebro.setbroker(qmt_broker)

    # live daily feed via miniQMT/xtdata
    qmt_data = qmtdata.QMTData(stock="512730.SH", period="1d")
    cerebro.adddata(qmt_data)

    cerebro.run()


if __name__ == '__main__':
    runstrategy()
'''
    stock_zh_a_hist_df = qmtdata
    data = bt.feeds.PandasData(dataname=stock_zh_a_hist_df, fromdate=start_date, todate=end_date)
'''
