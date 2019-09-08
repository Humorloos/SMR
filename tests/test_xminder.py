import os

from tests.shared import getEmptyCol
from xminder import XmindImporter
from XmindImport.consts import ADDON_PATH

def test_get_x_sheet():
    col = getEmptyCol()
    file = os.path.join(ADDON_PATH, 'tests', 'support', 'testmap1sheet.xmind')
    importer = XmindImporter(col=col, file=file)
    sheets = importer.get_x_sheets()
