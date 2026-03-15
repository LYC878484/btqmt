import datetime
import queue

import pandas as pd
import backtrader as bt
from backtrader.feed import DataBase
from xtquant import xtdata

from qmtstore import QMTStore


class MetaQMTData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        super(MetaQMTData, cls).__init__(name, bases, dct)
        QMTStore.DataCls = cls


class QMTData(DataBase, metaclass=MetaQMTData):
    """
    MiniQMT live data feed:
    - get_market_data 拉取历史K线
    - subscribe_quote 订阅tick并聚合成1m bar
    - 历史→实时切换，发送 LIVE 通知
    """

    params = (
        ("symbol", None),
        ("timeframe", bt.TimeFrame.Minutes),
        ("compression", 1),
        ("hist_period", "1m"),
        ("hist_count", 300),
    )

    lines = ("open", "high", "low", "close", "volume", "openinterest")

    _ST_HIST, _ST_LIVE, _ST_OVER = range(3)

    def __init__(self):
        super().__init__()
        self.q = queue.Queue()
        self._state = self._ST_HIST
        self._bar = None
        self._live = False
        # enforce timeframe/compression to match 1-minute bars
        self._timeframe = bt.TimeFrame.Minutes
        self._compression = 1

    # ----------------------------- start/stop -----------------------------
    def start(self):
        super().start()
        if not self.p.symbol:
            raise ValueError("QMTData requires symbol")
        self.symbol = self.p.symbol

        self._load_history()
        self._subscribe_tick()

    def stop(self):
        try:
            xtdata.unsubscribe_quote(stock_code=[self.symbol], period="tick")
        except Exception:
            pass
        self._state = self._ST_OVER
        super().stop()

    # ----------------------------- history -----------------------------
    def _load_history(self):
        fields = ["open", "high", "low", "close", "volume"]
        data = xtdata.get_market_data(
            fields=fields,
            stock_code=[self.symbol],
            period=self.p.hist_period,
            count=self.p.hist_count,
        )
        bars = data.get(self.symbol)
        if bars is None:
            return
        # bars is a DataFrame with datetime index
        for i in range(len(bars["close"])):
            dt = bars.index[i]
            if not isinstance(dt, datetime.datetime):
                dt = pd.to_datetime(dt)
            self.q.put(
                {
                    "type": "bar",
                    "datetime": dt,
                    "open": bars["open"][i],
                    "high": bars["high"][i],
                    "low": bars["low"][i],
                    "close": bars["close"][i],
                    "volume": bars["volume"][i],
                }
            )

    # ----------------------------- live subscribe -----------------------------
    def _subscribe_tick(self):
        def callback(data):
            try:
                tick_list = data.get(self.symbol)
                if not tick_list:
                    return
                tick = tick_list[0]
                price = tick.get("lastPrice") or tick.get("price")
                volume = tick.get("volume") or tick.get("match_qty") or 0
                ts = tick.get("time") or tick.get("datetime") or int(datetime.datetime.now().timestamp() * 1000)
                dt = datetime.datetime.fromtimestamp(ts / 1000)
                self.q.put({"type": "tick", "datetime": dt, "price": price, "volume": volume})
            except Exception:
                return

        xtdata.subscribe_quote(stock_code=[self.symbol], period="tick", callback=callback)

    # ----------------------------- tick -> bar -----------------------------
    def _tick_to_bar(self, tick):
        dt = tick["datetime"]
        price = tick["price"]
        volume = tick["volume"]

        minute = dt.replace(second=0, microsecond=0)
        if self._bar is None:
            self._bar = {
                "datetime": minute,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            return None

        if minute != self._bar["datetime"]:
            bar = self._bar
            self._bar = {
                "datetime": minute,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            return bar

        self._bar["high"] = max(self._bar["high"], price)
        self._bar["low"] = min(self._bar["low"], price)
        self._bar["close"] = price
        self._bar["volume"] += volume
        return None

    # ----------------------------- backtrader load -----------------------------
    def _load(self):
        try:
            msg = self.q.get(timeout=1)
        except queue.Empty:
            return None

        if msg["type"] == "bar":
            dt = msg["datetime"]
            self.lines.datetime[0] = bt.date2num(dt)
            self.lines.open[0] = msg["open"]
            self.lines.high[0] = msg["high"]
            self.lines.low[0] = msg["low"]
            self.lines.close[0] = msg["close"]
            self.lines.volume[0] = msg["volume"]
            self.lines.openinterest[0] = 0
            return True

        if msg["type"] == "tick":
            bar = self._tick_to_bar(msg)
            if bar is None:
                return None

            if self._state == self._ST_HIST:
                self._state = self._ST_LIVE
                self._live = True
                self._notify_data(self.LIVE)

            self.lines.datetime[0] = bt.date2num(bar["datetime"])
            self.lines.open[0] = bar["open"]
            self.lines.high[0] = bar["high"]
            self.lines.low[0] = bar["low"]
            self.lines.close[0] = bar["close"]
            self.lines.volume[0] = bar["volume"]
            self.lines.openinterest[0] = 0
            return True

        return None
