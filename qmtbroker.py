from datetime import datetime
import backtrader as bt
from backtrader import (TimeFrame, num2date, date2num, BrokerBase,
                        Order, OrderBase, OrderData)
from .qmtstore import QMTStore

class MetaQMTBroker(BrokerBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTBroker, cls).__init__(name, bases, dct)
        QMTStore.BrokerCls = cls


class QMTBroker(metaclass=MetaQMTBroker):
    pass