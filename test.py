from xtquant import xtdata
import time


def on_quote_data(data):
    """单只股票数据回调"""
    print("\n收到单只股票数据:")
    print(data)


# 订阅平安银行的分钟K线
seq = xtdata.subscribe_quote(
    stock_code="000001.SZ",  # 平安银行
    period="1m",             # 1分钟K线
    callback=on_quote_data   # 回调函数
)

print("开始接收实时数据...")
try:
    xtdata.run()
except KeyboardInterrupt:
    xtdata.unsubscribe_quote(seq)
    print("程序结束")