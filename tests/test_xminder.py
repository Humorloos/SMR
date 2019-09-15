import os

from xxmind import load

from tests.shared import getEmptyCol
from xminder import XmindImporter, SheetImport
from XmindImport.consts import ADDON_PATH

def test_get_x_sheet():
    col = getEmptyCol()
    file = os.path.join(ADDON_PATH, 'tests', 'support', 'testmap1sheet.xmind')
    importer = XmindImporter(col=col, file=file)
    sheets = importer.get_x_sheets()

def test_import_map():
    col = getEmptyCol()
    file = os.path.join(ADDON_PATH, 'tests', 'support', 'testmapmultsheet.xmind')
    importer = XmindImporter(col=col, file=file)
    doc = load(file)
    sheet = doc.getSheets()[0]
    sheet_import = SheetImport(sheet, 'hi')
    importer.importMap()