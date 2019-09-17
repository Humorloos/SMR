import json
import zipfile
import tempfile
import shutil
import urllib.parse

from time import sleep

from anki.importing.noteimp import NoteImporter

from xxmind import load
from xsheet import SheetElement

from sheetselectors import *
from utils import *

from XmindImport.consts import *


class SheetImport:
    def __init__(self, sheet: SheetElement, tag):
        self.sheet = sheet
        self.tag = tag
        self.deckId = None


class XmindImporter(NoteImporter):
    needMapper = False

    def __init__(self, col, file):
        NoteImporter.__init__(self, col, file)
        self.model = col.models.byName(X_MODEL_NAME)
        self.sheets = None
        self.mw = aqt.mw.app.activeWindow() or aqt.mw
        self.currentSheetImport = None
        self.mediaDir = os.path.join(os.path.dirname(col.path),
                                     'collection.media')
        self.srcDir = tempfile.mkdtemp()
        self.xZip = zipfile.ZipFile(file, 'r')
        self.warnings = []
        self.deckId = ''
        self.notesToAdd = list()
        self.running = True

    def run(self):
        selectedSheets = self.get_x_sheets()
        self.deckId = selectedSheets[0].deckId
        self.mw.progress.start(immediate=True)
        self.mw.checkpoint("Import")
        for sheetImport in selectedSheets:
            if self.running:
                self.importMap(sheetImport)

        # add all notes to collection
        if self.running:
            for note in self.notesToAdd:
                self.col.addNote(note)
            self.log = ['Imported %s notes' % len(self.notesToAdd)]
        self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
        print("fertig")

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
        if not selector.running:
            self.running = False
            self.log = ['Import canceled']
        return selector.sheets

    def importMap(self, sheetImport: SheetImport):
        rootTopic = sheetImport.sheet.getRootTopic()
        self.currentSheetImport = sheetImport
        # Set model to Stepwise map retrieval model
        xModel = self.col.models.byName(X_MODEL_NAME)
        self.col.decks.select(self.currentSheetImport.deckId)
        self.col.decks.current()['mid'] = xModel['id']
        # create first notes for this sheet
        notes = list()
        # noinspection PyUnusedLocal
        for question in rootTopic.getSubTopics():
            notes.append(self.col.newNote())
            sleep(0.001)
        rootDict = dict(subTopic=rootTopic, isAnswer=True, aId=str(1))
        self.getQuestions(answerDict=rootDict, notes=notes,
                          ref=rootTopic.getTitle())

    # calls createNotes for each answer.
    # Inputs:
    # answer: parent answer node of the questions to get
    # notes: list of notes for the notes to be created from the gotten questions
    # AnswerContent: content of parent answer in parent anki note
    # ref: current text for reference field
    # aId: current id for id field
    def getQuestions(self, answerDict: dict, notes: list, answerContent='',
                     ref="", aId=""):
        if not answerDict['subTopic'].getParentNode().tagName == 'sheet':
            if isEmptyNode(answerDict['subTopic']):
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + answerContent + '</li>'
        questionDicts = findQuestionDicts(answer=answerDict['subTopic'],
                                          ref=ref)
        for qId, questionDict in enumerate(questionDicts, start=1):
            nextId = aId + getId(qId)
            if not (len(questionDict['question'].getSubTopics()) > 0):
                self.running = False
                self.log = ["""Warning:
A Question titled "%s" (Path %s) is missing answers. Please adjust your Concept Map and try again.""" %
                            (questionDict['question'].getTitle(), aId)]
            if self.running:
                self.addNote(question=questionDict['question'],
                             ref=questionDict['ref'], qId=nextId,
                             note=notes[qId - 1])

    # Inputs:
    # question: xmind question node
    # ref: current reference text
    # qId: position of the question node relative to its siblings
    # note: note to be added for the question node
    # creates notes for the children of this note, configures this note and
    # recursively calls getQuestions() to add notes following this note
    def addNote(self, question: TopicElement, ref, qId, note):

        answerDicts = self.findAnswerDicts(question)

        if self.running:
            # Create Notes for next questions for Question nids in Meta field
            nextNotes = self.getNextNotes(answerDicts)

            # configure and add note to collection
            self.makeXNote(note=note, qId=qId, question=question,
                           answerDicts=answerDicts, ref=ref,
                           nextNotes=nextNotes)

            # add notes for questions following this note
            ref = ref + '<li>' + question.getTitle()
            for aId, answerDict in enumerate(answerDicts, start=1):
                if answerDicts[aId - 1]['isAnswer']:
                    answerContent = note.fields[list(X_FLDS.keys()).index(
                        'a' + answerDict['aId'])]
                else:
                    answerContent = ''
                self.getQuestions(
                    answerDict=answerDict, notes=nextNotes[aId - 1],
                    answerContent=answerContent,
                    ref=ref, aId=qId + getId(aId))

    # TODO: check out hierarchical tags, may be useful

    # receives a question, sheet and list of notes possibly following this question and returns a json file
    def getXMindMeta(self, question: TopicElement, notes: list, nAnswers):
        xMindMeta = dict()
        xMindMeta['path'] = self.file
        xMindMeta['sheetId'] = self.currentSheetImport.sheet.getID()
        xMindMeta['questionId'] = question.getID()
        xMindMeta['answers'] = list()
        subTopics = question.getSubTopics()
        for sId, subTopic in enumerate(subTopics, start=0):
            xMindMeta['answers'].append(dict())
            xMindMeta['answers'][sId]['answerId'] = subTopics[sId].getID()
            xMindMeta['answers'][sId]['children'] = list()
            for note in notes[sId]:
                xMindMeta['answers'][sId]['children'].append(note.id)
        xMindMeta['nAnswers'] = nAnswers
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

    # get the content of a node as string and add files to the collection if
    # necessary
    def getContent(self, node: TopicElement):
        content = ''
        if node.getTitle():
            content += node.getTitle()
        # if necessary add image
        try:
            attachment = node.getFirstChildNodeByTagName('xhtml:img'). \
                             getAttribute('xhtml:src')[4:]
            self.addImage(attachment)
            if content != '':
                content += '<br>'
            content += '<img src="%s">' % attachment[12:]
        except:
            pass
        # if necessary add audio file
        audioAttr = node.getAttribute('xlink:href')
        if audioAttr:
            if content != '':
                content += '<br>'
            content += '[sound:%s]' % self.addAudio(audioAttr)
        return content

    # receives a list of answerDicts and returns a list of anki notes for each
    # subtopic
    def getNextNotes(self, answerDicts: list):
        nextNotes = []
        for answerDict in answerDicts:
            # Add one new note for each question following this subTopic
            noteListForQuestions = self.getNoteListForQuestions(
                answerDict['subTopic'])
            nextNotes.append(noteListForQuestions)
        return nextNotes

    # receives an xmind node and returns a list of anki notes containing one
    # note for each question following this node
    def getNoteListForQuestions(self, subTopic: TopicElement):
        noteList = []
        questions = subTopic.getSubTopics()
        for question in questions:
            if not (isEmptyNode(question)):
                noteList.append(self.col.newNote())
            else:
                nextAnswerDicts = self.findAnswerDicts(question)
                # code in brackets is for unlisting:
                # https://stackoverflow.com/a/952952
                followingNotes = [item for sublist in self.getNextNotes(
                    nextAnswerDicts) for item in sublist]
                noteList.extend(followingNotes)
            # wait some milliseconds to create note with a different nid
            sleep(0.001)
        return noteList

    # sets the deck, fields and tag of an xmind note and adds it to the
    # collection
    def makeXNote(self, note, qId, question, answerDicts, ref, nextNotes):
        # Set deck
        note.model()['did'] = self.currentSheetImport.deckId

        # set field ID
        note.fields[list(X_FLDS.keys()).index('id')] = qId

        # Set field Question
        note.fields[list(X_FLDS.keys()).index('qt')] = self.getContent(question)

        # Set Answer fields
        aId = 0
        for answerDict in answerDicts:
            if answerDict['isAnswer']:
                aId += 1
                note.fields[list(X_FLDS.keys()).index('a' + str(aId))] = \
                    self.getContent(answerDict['subTopic'])
                answerDict['aId'] = str(aId)

        # Set field Reference
        note.fields[list(X_FLDS.keys()).index('rf')] = '<ul>%s</ul>' % ref

        # set field Meta
        meta = self.getXMindMeta(question=question, notes=nextNotes,
                                 nAnswers=aId)
        note.fields[list(X_FLDS.keys()).index('mt')] = meta

        # Set tag
        note.tags.append(self.currentSheetImport.tag)

        # add to col
        self.notesToAdd.append(note)

    # receives a question node and returns a list of dictionaries containing the
    # subtopics and whether the subtopics contain an answer or not
    def findAnswerDicts(self, question: TopicElement):
        answerDicts = list()
        for subTopic in question.getSubTopics():
            isAnswer = True
            if isEmptyNode(subTopic):
                isAnswer = False
            answerDicts.append(
                dict(subTopic=subTopic, isAnswer=isAnswer, aId=str(0)))
        actualAnswers = list(filter(
            lambda answerDict: answerDict['isAnswer'], answerDicts))
        if len(actualAnswers) > X_MAX_ANSWERS:
            self.running = False
            self.log = ["""Warning:
A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than 20 Answers and try again.""" %
                        (question.getTitle(), X_MAX_ANSWERS)]
        return answerDicts
