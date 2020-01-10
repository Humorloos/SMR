import os
import sys
import pickle

from unittest import TestCase

from XmindImport.sheetselectors import SingleSheetSelector, MultiSheetSelector
from XmindImport.consts import ADDON_PATH

from PyQt5 import QtWidgets

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'sheetselectors')


class TestSheetSelector(TestCase):
    def setUp(self):
        self.app = QtWidgets.QApplication(sys.argv)


class TestSingleSheetSelector(TestSheetSelector):
    def setUp(self):
        super().setUp()
        self.filename = 'example_map.xmind'
        self.singleSheetSelector = SingleSheetSelector(self.filename)


class TestInitSingle(TestSingleSheetSelector):
    def test_singleSheetSelector(self):
        self.singleSheetSelector.show()
        self.app.exec_()
        act = self.singleSheetSelector.getInputs()
        print('done')


class TestMultiSheetSelector(TestSheetSelector):
    def setUp(self):
        super().setUp()
        self.sheets = ['biological psychology', 'clinical psychology',
                       'general psychology']
        self.multiSheetSelector = MultiSheetSelector(self.sheets)


class TestInitMulti(TestMultiSheetSelector):
    def test_multiSheetSelector(self):
        self.multiSheetSelector.show()
        self.app.exec_()
        act = self.multiSheetSelector.getInputs()
        print('done')
