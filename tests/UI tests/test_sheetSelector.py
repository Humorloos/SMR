import sys
from unittest import TestCase

from PyQt5 import QtWidgets
from XmindImport.sheetselectors import DeckSelectionDialog


class TestSheetSelector(TestCase):
    def setUp(self):
        self.app = QtWidgets.QApplication(sys.argv)


class TestSingleSheetSelector(TestSheetSelector):
    def setUp(self):
        super().setUp()
        self.filename = 'example_map.xmind'
        self.singleSheetSelector = DeckSelectionDialog(self.filename)


class TestInitSingle(TestSingleSheetSelector):
    def test_singleSheetSelector(self):
        """
        Simple UI test for deck selection dialog
        """
        self.singleSheetSelector.show()
        self.app.exec_()
        act = self.singleSheetSelector.get_inputs()
        print('done')
