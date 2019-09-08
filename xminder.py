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
        selected_sheets = self.get_x_sheets()
        print("fertig")

    # returns list of
    def get_x_sheets(self):
        mw = aqt.mw.app.activeWindow() or aqt.mw
        mw.progress.finish()
        doc = load(self.file)
        imp_sheets = doc.getSheets()
        doc_title = os.path.basename(self.file)[:-6]
        if len(imp_sheets) > 1:
            selector = MultiSheetSelector(imp_sheets, doc_title)
        else:
            selector = SingleSheetSelector(imp_sheets, doc_title)
        selector.exec_()
        return selector.sheets


class SheetImport:
    def __init__(self, sheet, tag):
        self.sheet = sheet
        self.tag = tag
