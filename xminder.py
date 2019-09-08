from anki.importing.noteimp import NoteImporter

from xxmind import load
from sheetselectors import *

from XmindImport.consts import *

class XmindImporter(NoteImporter):
    needMapper = False

    def __init__(self, col, file):
        NoteImporter.__init__(self, col, file)
        self.model = col.models.byName(X_MODEL_NAME)
        self.sheets = None


    def run(self):
        self.log = ['fertig']
        self.get_x_sheets()


    def get_x_sheets(self):
        mw = aqt.mw.app.activeWindow() or aqt.mw
        mw.progress.finish()
        doc = load(self.file)
        imp_sheets = doc.getSheets()
        if len(imp_sheets) > 1:
            selector = MultiSheetSelector(imp_sheets)
        else:
            selector = SingleSheetSelector(imp_sheets[0])
        selector.exec_()
        return


class SheetImport:
    def __init__(self, sheet, tag):
        self.sheet = sheet
        self.tag = tag
