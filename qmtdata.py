import datetime

import backtrader as bt
from backtrader.feed import DataBase
from .qmtstore import QMTStore

class MetaQMTData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTData, cls).__init__(name, bases, dct)

        # Register with the store
        QMTStore.DataCls = cls

class QMTData(metaclass=MetaQMTData):
    pass