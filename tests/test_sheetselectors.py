import os
import sys
import pickle

from XmindImport.sheetselectors import SingleSheetSelector, MultiSheetSelector
from XmindImport.consts import ADDON_PATH

from PyQt5 import QtWidgets

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'sheetselectors')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    sheetImport = {'biological psychology': pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetImports.p'), "rb"))[
        'biological psychology']}
    Dialog = SingleSheetSelector(sheetImport)
    Dialog.show()
    app.exec_()
    act = Dialog.sheetImports
    print('done')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    sheetImports = pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetImports.p'), "rb"))
    Dialog = MultiSheetSelector(sheetImports)
    Dialog.show()
    app.exec_()
    act = Dialog.sheetImports
    print('done')
