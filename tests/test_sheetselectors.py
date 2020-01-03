import os
import sys
import pickle

from XmindImport.sheetselectors import SingleSheetSelector, MultiSheetSelector
from XmindImport.consts import ADDON_PATH

from PyQt5 import QtWidgets

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'sheetselectors')

# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     file = os.path.join(ADDON_PATH, 'tests', 'support', 'testmap1sheet.xmind')
#     doc = load(file)
#     sheet = doc.getSheets()
#     Dialog = SingleSheetSelector(sheet, os.path.basename(file)[:-6])
#     Dialog.show()
#     sys.exit(app.exec_())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    sheetImports = pickle.load(open(os.path.join(SUPPORT_PATH, 'sheetImports.p'), "rb"))
    Dialog = MultiSheetSelector(sheetImports)
    Dialog.show()
    app.exec_()
    act = Dialog.sheetImports
    print('done')
