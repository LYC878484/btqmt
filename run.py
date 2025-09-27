import backtrader as bt
import qmtstore
import qmtbroker
import qmtdata

def runstrategy():
    # Create a cerebro
    cerebro = bt.Cerebro()

    qmt_store = qmtstore.QMTStore()
    qmt_broker = qmtbroker.QMTBroker()


    #stock = '600000.SH'
    qmt_data = qmtdata.QMTData()
    cerebro.setbroker(qmt_broker)

    #hisdata = qmt_data.history_data(stock="600406.SH", period="1d", start="20240101", end="20240401")
    #print(hisdata)

    seq = qmt_data.subscribe_live_data(stock="512730.SH", period="1d", start="20240101", end="20240401")

    #cerebro.adddata(data0)


    cerebro.run()


if __name__ == '__main__':
    runstrategy()
'''
    stock_zh_a_hist_df = qmtdata
    data = bt.feeds.PandasData(dataname=stock_zh_a_hist_df, fromdate=start_date, todate=end_date)
'''