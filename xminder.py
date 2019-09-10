from anki.importing.noteimp import NoteImporter
from anki.lang import _
from anki.collection import _Collection

from xxmind import load
from xsheet import SheetElement
from xtopic import TopicElement

from sheetselectors import *

from XmindImport.consts import *


class SheetImport:
    def __init__(self, sheet: SheetElement, tag):
        self.sheet = sheet
        self.tag = tag
        self.deckId = None


class XmindImporter(NoteImporter):
    needMapper = False

    def __init__(self, col: _Collection, file):
        NoteImporter.__init__(self, col, file)
        self.model = col.models.byName(X_MODEL_NAME)
        self.sheets = None
        self.mw = aqt.mw.app.activeWindow() or aqt.mw
        self.deckId = None

    def run(self):
        selectedSheets = self.get_x_sheets()
        self.deckId = selectedSheets[0].deckId
        for sheetImport in selectedSheets:
            self.importMap(sheetImport)
        print("fertig")
        self.log = ['fertig']

    # returns list of
    def get_x_sheets(self):
        doc = load(self.file)
        imp_sheets = doc.getSheets()
        doc_title = os.path.basename(self.file)[:-6]
        if len(imp_sheets) > 1:
            selector = MultiSheetSelector(imp_sheets, doc_title)
        else:
            selector = SingleSheetSelector(imp_sheets, doc_title)
        self.mw.progress.finish()
        selector.exec_()
        return selector.sheets

    def importMap(self, sheetImport: SheetImport):
        self.mw.progress.start(immediate=True)
        self.mw.checkpoint(_("Import"))
        rootTopic = sheetImport.sheet.getRootTopic()
        self.getQuestions(rootTopic)

        self.mw.progress.finish()

    def getQuestions(self, answer: TopicElement, ref="", aId=""):
        if answer.getParentNode().tagName == 'sheet':
            ref = answer.getTitle()
        else:
            ref = ref + '\n' +  ': ' + answer.getTitle()
        for qId, question in enumerate(answer.getSubTopics(), start=1):
            nextId = aId + self.getId(qId)
            self.createNotes(question=question, ref=ref, qId=nextId)

    def createNotes(self, question: TopicElement, ref, qId):
        self.col.models.setCurrent(self.col.models.byName(X_MODEL_NAME))
        deck = self.col.decks.get(self.deckId)
        note = self.col.newNote()
        # set note fields
        note.fields[0] = qId
        note.fields[1] = question.getTitle()
        answers = question.getSubTopics()
        for aId, answer in enumerate(answers, start = 1):
            note.fields[1 + aId] = answer.getTitle()
        note.fields[X_MAX_ANSWERS + 2] = ref
        meta = ""
        note.fields[X_MAX_ANSWERS + 3] = meta

        for answer in answers:
            ref = ref + '\n' + answer.getTitle()



        a = 0

    # returns numbers 1 : 9 or letters starting with A starting at 10
    def getId(self, id):
        if id < 10:
            return str(id)
        else:
            return chr(id + 55)
