import json
import zipfile
import tempfile
import shutil
import urllib.parse

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
        self.currentSheetImport = None
        self.mediaDir = os.path.join(os.path.dirname(col.path),
                                     'collection.media')
        self.srcDir = tempfile.mkdtemp()
        self.xZip = zipfile.ZipFile(file, 'r')

    def run(self):
        selectedSheets = self.get_x_sheets()
        self.deckId = selectedSheets[0].deckId
        self.mw.progress.start(immediate=True)
        self.mw.checkpoint(_("Import"))
        for sheetImport in selectedSheets:
            self.importMap(sheetImport)
        self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
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
        rootTopic = sheetImport.sheet.getRootTopic()
        self.currentSheetImport = sheetImport
        # Set model to Stepwise map retrieval model
        xModel = self.col.models.byName(X_MODEL_NAME)
        self.col.decks.select(self.currentSheetImport.deckId)
        self.col.decks.current()['mid'] = xModel['id']
        # self.col.models.setCurrent(self.col.models.byName(X_MODEL_NAME))
        notes = list()
        for i in rootTopic.getSubTopics():
            # forDeck=False so that the chosen model does not depend on the deck
            notes.append(self.col.newNote())
            sleep(0.001)
        self.getQuestions(answer=rootTopic, notes=notes,
                          ref=rootTopic.getTitle())

    # calls createNotes for each answer
    def getQuestions(self, answer: TopicElement, notes: list, ref="", aId=""):
        if not answer.getParentNode().tagName == 'sheet':
            ref = ref + ': ' + answer.getTitle() + '</li>'
        for qId, question in enumerate(answer.getSubTopics(), start=1):
            nextId = aId + self.getId(qId)
            self.createNote(question=question, ref=ref,
                            qId=nextId, note=notes[qId - 1])

    # fills an Anki note for a given question and its answers
    def createNote(self, question: TopicElement, ref, qId, note):
        # Set deck
        note.model()['did'] = self.currentSheetImport.deckId
        # set field ID
        note.fields[0] = qId
        # Set field Question
        note.fields[1] = self.getContent(question)
        answers = question.getSubTopics()
        nextNotes = list()
        for aId, answer in enumerate(answers, start=1):
            # Set Answer fields
            note.fields[1 + aId] = self.getContent(answer)
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
        meta = self.getXMindMeta(question=question, notes=nextNotes)
        note.fields[X_MAX_ANSWERS + 3] = meta
        # Set tag
        note.tags.append(self.currentSheetImport.tag)
        self.col.addNote(note)

        ref = ref + '<li>' + question.getTitle()
        # make notes for following cards
        for aId, answer in enumerate(answers, start=1):
            self.getQuestions(answer=answer, notes=nextNotes[aId - 1], ref=ref,
                              aId=qId + self.getId(aId))

    # returns numbers 1 : 9 or letters starting with A starting at 10
    def getId(self, id):
            return chr(id + 64)

    # receives a question, sheet and list of notes possibly following this question and returns a json file
    def getXMindMeta(self, question: TopicElement, notes: list):
        xMindMeta = dict()
        xMindMeta['path'] = self.file
        xMindMeta['sheetId'] = self.currentSheetImport.sheet.getID()
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

    def addImage(self, attachment):
        # extract image to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.addFile(srcPath)

    def addAudio(self, audioAttr):
        audioPath = urllib.parse.unquote(audioAttr[7:])
        audioExt = os.path.splitext(audioPath)[1]
        if audioExt in ['.mp3', '.wav']:
            self.col.media.addFile(audioPath)
        return os.path.basename(audioPath)

    def getContent(self, node: TopicElement):
        content = node.getTitle()
        # if necessary add image
        try:
            attachment = node.getFirstChildNodeByTagName('xhtml:img').\
                             getAttribute('xhtml:src')[4:]
            self.addImage(attachment)
            content = content + '<br><img src="%s">' % attachment[12:]
        except:
            pass
        # if necessary add audio file
        audioAttr = node.getAttribute('xlink:href')
        if audioAttr:
            content = content + '<br>[sound:%s]' % self.addAudio(audioAttr)
        return content