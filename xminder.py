import json

from time import sleep

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
        self.tag = ""

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
        self.tag = sheetImport.tag
        self.col.models.setCurrent(self.col.models.byName(X_MODEL_NAME))
        deck = self.col.decks.get(self.deckId)
        notes = list()
        for i in rootTopic.getSubTopics():
            notes.append(self.col.newNote())
        self.getQuestions(answer=rootTopic, sheet=sheetImport.sheet,
                          notes=notes)

        self.mw.progress.finish()

    def getQuestions(self, answer: TopicElement, sheet: SheetElement,
                     notes: list, ref="", aId=""):
        if answer.getParentNode().tagName == 'sheet':
            ref = answer.getTitle()
        else:
            ref = ref + '\n' +  ': ' + answer.getTitle()
        for qId, question in enumerate(answer.getSubTopics(), start=1):
            nextId = aId + self.getId(qId)
            self.createNotes(question=question, sheet=sheet, ref=ref,
                             qId=nextId, note=notes[qId - 1])

    def createNotes(self, question: TopicElement, sheet: SheetElement, ref,
                    qId, note):
        # Set tag
        note.tags.append(self.tag)

        # set field ID
        note.fields[0] = qId
        # Set field Question
        note.fields[1] = question.getTitle()

        answers = question.getSubTopics()
        nextNotes = list()
        for aId, answer in enumerate(answers, start = 1):
            # Set Answer fields
            note.fields[1 + aId] = answer.getTitle()
            # Create Notes for next questions for Question nids in Meta field
            nextQs = answer.getSubTopics()
            # Add list for questions of this answer
            nextNotes.append(list())
            # Add one new note for each question following this answer
            for i in nextQs:
                nextNotes[aId - 1].append(self.col.newNote())
                # wait some milliseconds to create note with a different nid
                sleep(0.001)
        # Set field Reference
        note.fields[X_MAX_ANSWERS + 2] = ref
        # set field Meta
        meta = self.getXMindMeta(question=question, sheet=sheet,
                                 notes=nextNotes)
        note.fields[X_MAX_ANSWERS + 3] = meta

        for answer in answers:
            ref = ref + '\n' + answer.getTitle()

        self.col.addNote(note)

        a = 0

    # returns numbers 1 : 9 or letters starting with A starting at 10
    def getId(self, id):
        if id < 10:
            return str(id)
        else:
            return chr(id + 55)

    # receives a question, sheet and list of notes possibly following this question and returns a json file
    def getXMindMeta(self, question: TopicElement, sheet: SheetElement,
                     notes: list):
        xMindMeta = dict()
        xMindMeta['sheetId'] = sheet.getID()
        xMindMeta['questionId'] = question.getID()
        xMindMeta['answers'] = list()
        answers = question.getSubTopics()
        for aId, answer in enumerate(answers, start=0):
            xMindMeta['answers'].append(dict())
            xMindMeta['answers'][aId]['answerId'] = answers[aId].getID()
            xMindMeta['answers'][aId]['children'] = list()
            for note in notes[aId]:
                xMindMeta['answers'][aId]['children'].append(note.id)
        return json.dumps(xMindMeta)


