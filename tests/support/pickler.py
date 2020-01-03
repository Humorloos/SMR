# creates support files for tests

import os
import pickle
import sys

from bs4 import BeautifulSoup
from PyQt5 import QtWidgets

from tests.shared import getEmptyCol

from XmindImport.consts import ADDON_PATH
from XmindImport.xminder import XmindImporter
from XmindImport.sheetselectors import MultiSheetSelector

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


def getSheetImports():
    col = getEmptyCol()
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    xmindImporter = XmindImporter(col=col, file=map)
    sheetImports = xmindImporter.get_x_sheets(
        xmindImporter.soup, xmindImporter.file)[1]
    pickle.dump(sheetImports, open(
        os.path.join(SUPPORT_PATH, 'sheetSelectors', 'sheetImports.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetSelectors', 'sheetImports.p'),
             'rb'))


def getSelectedSheets():
    app = QtWidgets.QApplication(sys.argv)
    sheetImports = pickle.load(
        open(os.path.join(SUPPORT_PATH, 'sheetselectors', 'sheetImports.p'),
             "rb"))
    Dialog = MultiSheetSelector(sheetImports)
    Dialog.show()
    app.exec_()
    selectedSheets = Dialog.getInputs()['sheetImports']
    pickle.dump(selectedSheets, open(
        os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'), 'wb'))
    return pickle.load(
        open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'selectedSheets.p'),
             'rb'))


def getSheetBiologicalPsychology():
    col = getEmptyCol()
    map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    xmindImporter = XmindImporter(col=col, file=map)
    sheets = xmindImporter.get_x_sheets(
        xmindImporter.soup, xmindImporter.file)[0]
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'w') as file:
        file.write(str(sheets['biological psychology']))
    with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                           'sheet_biological_psychology.xml'), 'r') as file:
        return BeautifulSoup(file.read(), features='html.parser')


sheetImports = getSheetImports()
selectedSheets = getSelectedSheets()
sheetBiologicalPsychology = getSheetBiologicalPsychology()
