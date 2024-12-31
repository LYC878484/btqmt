import datetime

import backtrader as bt
from backtrader.feed import DataBase
import qmtstore

class MetaQMTData(DataBase.__class__):
    def __init__(cls, name, bases, dct):
        '''Class has already been created ... register'''
        # Initialize the class
        super(MetaQMTData, cls).__init__(name, bases, dct)

        # Register with the store
        qmtstore.QMTStore.DataCls = cls

class QMTData(metaclass=MetaQMTData):
    _store = qmtstore.QMTStore
    def __init__(self, **kwargs):
        self.qmt = self._store(**kwargs)

    def setenvironment(self, env):
        '''Receives an environment (cerebro) and passes it over to the store it
        belongs to'''
        super(QMTData, self).setenvironment(env)
        env.addstore(self.qmt)

    def start(self):
        '''Starts the QMT connecction and gets the real contract and
        contractdetails if it exists'''
        super(QMTData, self).start()

    def stop(self):
        '''Stops and tells the store to stop'''
        super(QMTData, self).stop()
        #self.qmt.stop()