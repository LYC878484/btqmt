from datetime import datetime
import backtrader as bt
from backtrader import (TimeFrame, num2date, date2num, BrokerBase,
                        Order, OrderBase, OrderData)
import qmtstore

class MetaQMTBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTBroker, cls).__init__(name, bases, dct)
        qmtstore.QMTStore.BrokerCls = cls


class QMTBroker(metaclass=MetaQMTBroker):
    def __init__(self, **kwargs):
        super(QMTBroker, self).__init__()
        self.qmt = qmtstore.QMTStore(**kwargs)

    def start(self):
        super(QMTBroker, self).start()
        self.qmt.start(broker=self)

    def stop(self):
        super(QMTBroker, self).stop()
        #self.qmt.stop()

    def buy(self, owner, data,
            size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0,
            **kwargs):
        pass

    def sell(self, owner, data,
            size, price=None, plimit=None,
            exectype=None, valid=None, tradeid=0,
            **kwargs):
        pass
