import os
import sys

from XmindImport.xmind.xxmind import load

from XmindImport.sheetselectors import SingleSheetSelector, MultiSheetSelector
from XmindImport.consts import ADDON_PATH

from PyQt5 import QtWidgets

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
    file = os.path.join(ADDON_PATH, 'tests', 'support',
                        'testmapmultsheet.xmind')
    doc = load(file)
    sheets = doc.getSheets()
    Dialog = MultiSheetSelector(sheets, os.path.basename(file)[:-6])
    Dialog.show()
    sys.exit(app.exec_())
