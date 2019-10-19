import json
import zipfile
import tempfile
import shutil
import urllib.parse
import re

from bs4 import BeautifulSoup
from time import sleep

from anki.importing.noteimp import NoteImporter

from XmindImport.xmind.xxmind import load
from XmindImport.xmind.xsheet import SheetElement

from XmindImport.sheetselectors import *
from XmindImport.utils import *
from XmindImport.consts import *


# TODO: add warning when something is wrong with the map
# TODO: add synchronization feature
# TODO: change absolute to relative paths
# TODO: add new prestentation order
# TODO: Implement hints as part of the meta json instead of javascript and use
#  sound=False to mute answers in hint
# TODO: Implement warning if an audio file can't be found
# TODO: Use highest symbol in anki sorting mechanism for separator in ID codes

class XmindImporter(NoteImporter):
    needMapper = False

    def __init__(self, col, file):
        NoteImporter.__init__(self, col, file)
        self.model = col.models.byName(X_MODEL_NAME)
        self.sheets = None
        self.mw = aqt.mw.app.activeWindow() or aqt.mw
        self.currentSheetImport = dict()
        self.mediaDir = os.path.join(os.path.dirname(col.path),
                                     'collection.media')
        self.srcDir = tempfile.mkdtemp()
        self.xZip = zipfile.ZipFile(file, 'r')
        self.warnings = []
        self.deckId = ''
        self.notesToAdd = list()
        self.running = True
        self.soup = None

    def run(self):
        selectedSheets = self.get_x_sheets()
        self.deckId = selectedSheets[0]['deckId']
        self.mw.progress.start(immediate=True)
        self.mw.checkpoint("Import")
        for sheetImport in selectedSheets:
            if self.running:
                self.importMap(sheetImport)

        # add all notes to collection
        if self.running:
            for noteDict in self.notesToAdd:
                self.col.addNote(self.noteFromNoteDict(noteDict))
                sleep(0.001)
            self.log = ['Imported %s notes' % len(self.notesToAdd)]
        self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
        print("fertig")

    # returns list of
    def get_x_sheets(self):
        doc = load(self.file)
        self.soup = BeautifulSoup(doc.getOwnerDocument().toxml(),
                                  features='html.parser')
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

    def importMap(self, sheetImport: dict):
        rootTopic = sheetImport['sheet'].getRootTopic()
        self.currentSheetImport = sheetImport
        # Set model to Stepwise map retrieval model
        xModel = self.col.models.byName(X_MODEL_NAME)
        self.col.decks.select(self.currentSheetImport['deckId'])
        self.col.decks.current()['mid'] = xModel['id']
        rootDict = dict(subTopic=rootTopic, isAnswer=True, aId=str(1))
        self.getQuestions(answerDict=rootDict, ref=rootTopic.getTitle())

    # calls createNotes for each answer.
    # Inputs:
    # answer: parent answer node of the questions to get
    # notes: list of notes for the notes to be created from the gotten questions
    # AnswerContent: content of parent answer in parent anki note
    # ref: current text for reference field
    # aId: current id for id field
    def getQuestions(self, answerDict: dict, sortId='',
                     answerContent='', ref=""):
        # The reference doesn't have to be edited at the roottopic
        if not answerDict['subTopic'].getParentNode().tagName == 'sheet':
            # if the answerdict contains nothing (i.e. questions
            # following multiple answers), just close the reference
            if isEmptyNode(answerDict['subTopic']):
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + answerContent + '</li>'
        questionDicts = findQuestionDicts(answer=answerDict['subTopic'],
                                          ref=ref)

        for qId, questionDict in enumerate(questionDicts, start=1):
            # Update the sorting ID
            nextSortId = updateId(previousId=sortId, idToAppend=qId)
            # stop and warn if no nodes follow the question
            if not (len(questionDict['question'].getSubTopics()) > 0):
                self.running = False
                self.log = ["""Warning:
A Question titled "%s" (Path %s) is missing answers. Please adjust your Concept Map and try again.""" %
                            (questionDict['question'].getTitle(),
                             getCoordsFromId(sortId))]
            if self.running:
                self.addNote(question=questionDict['question'],
                             ref=questionDict['ref'], sortId=nextSortId)

    # Inputs:
    # question: xmind question node
    # ref: current reference text
    # qId: position of the question node relative to its siblings
    # note: note to be added for the question node
    # creates notes for the children of this note, configures this note and
    # recursively calls getQuestions() to add notes following this note
    def addNote(self, question: TopicElement, ref, sortId):

        answerDicts = self.findAnswerDicts(question)

        if self.running:
            # Create Notes for next questions for Question nids in Meta field
            nextQuestions = self.getNextQuestions(answerDicts)

            # get content of fields for the note to add for this question
            noteDict = self.getNoteDict(sortId=sortId, question=question,
                                        answerDicts=answerDicts, ref=ref,
                                        nextQuestions=nextQuestions)
            # add to list of notes to add
            self.notesToAdd.append(noteDict)

            # add notes for questions following this note
            questionContent = replaceSound(noteDict['qt'])
            ref = ref + '<li>' + questionContent
            for aId, answerDict in enumerate(answerDicts, start=1):
                if answerDicts[aId - 1]['isAnswer']:
                    answerContent = replaceSound(
                        noteDict['an']['a' + answerDict['aId']])
                else:
                    answerContent = ''
                self.getQuestions(answerDict=answerDict,
                                  answerContent=answerContent, ref=ref,
                                  sortId=updateId(previousId=sortId,
                                                  idToAppend=aId))

    # TODO: check out hierarchical tags, may be useful

    # receives a question, sheet and list of notes possibly following each
    # answer to this question and returns a json file
    def getXMindMeta(self, question: TopicElement, nextQuestions: list,
                     answerDicts):
        xMindMeta = dict()
        xMindMeta['path'] = self.file
        xMindMeta['sheetId'] = self.currentSheetImport['sheet'].getID()
        xMindMeta['questionId'] = question.getID()
        xMindMeta['answers'] = []
        globalQuestions = []
        nAnswers = 0
        for aId, answerDict in enumerate(answerDicts, start=0):
            # write each answer and its following questions into meta
            if answerDict['isAnswer']:
                xMindMeta['answers'].append(dict())
                xMindMeta['answers'][nAnswers]['answerId'] = answerDict[
                    'subTopic'].getID()
                xMindMeta['answers'][nAnswers]['children'] = []
                for question in nextQuestions[aId]:
                    xMindMeta['answers'][nAnswers]['children'].append(
                        question.getID())
                nAnswers += 1
            # add questions following bridges to globalQuestions
            else:
                globalQuestions.extend(nextQuestions[aId])
        # add globalQuestions to children of all answers
        for question in globalQuestions:
            for answer in xMindMeta['answers']:
                answer['children'].append(question.getID())
        xMindMeta['nAnswers'] = nAnswers
        return json.dumps(xMindMeta)

    def addImage(self, attachment):
        # extract image to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.addFile(srcPath)

    # gets an link attribute from an xmind file checks whether it relates to an
    # audio file with ending .mp3 or .wav, adds the file to the anki collection
    # and returns the audio's basename
    def addAudio(self, audioAttr):
        inMap = False
        if audioAttr.startswith('file'):
            audioPath = urllib.parse.unquote(audioAttr[7:])
        elif audioAttr.startswith('xap'):
            inMap = True
            audioPath = audioAttr[4:]
        else:
            audioPath = urllib.parse.unquote(audioAttr[7:])
        audioExt = os.path.splitext(audioPath)[1]
        if audioExt in ['.mp3', '.wav']:
            if inMap:
                # extract file and add it to temporary source directory
                self.xZip.extract(audioPath, self.srcDir)
                audioPath = os.path.join(self.srcDir, audioPath)
            self.col.media.addFile(audioPath)
        return os.path.basename(audioPath)

    # get the content of a node as string and add files to the collection if
    # necessary
    def getContent(self, node: TopicElement):
        content = ''
        href = node.getHyperlink()
        if node.getTitle():
            content += node.getTitle()

        # If the node contains a link to another node, add the text of that
        # node. Use Beautifulsoup because minidom can't find nodes by attributes
        if href and href.startswith('xmind:#'):
            if content != '':
                content += ' '
            content += self.soup.find('topic', {'id': href[7:]}).next.text

        # if necessary add image
        try:
            attachment = node.getFirstChildNodeByTagName('xhtml:img'). \
                             getAttribute('xhtml:src')[4:]
            self.addImage(attachment)
            if content != '':
                content += '<br>'
            fileName = re.search('/.*', attachment).group()[1:]
            content += '<img src="%s">' % fileName
        except:
            pass
        # if necessary add audio file
        if href and href.endswith(('.mp3', '.wav')):
            if content != '':
                content += '<br>'
            content += '[sound:%s]' % self.addAudio(href)
        return content

    # receives a list of answerDicts and returns a list of anki notes for each
    # subtopic
    def getNextQuestions(self, answerDicts: list):
        nextNotes = []
        for answerDict in answerDicts:
            # Add one new note for each question following this subTopic
            noteListForQuestions = self.getQuestionListForAnswer(
                answerDict)
            nextNotes.append(noteListForQuestions)
        return nextNotes

    # TODO: Use getTopicById() and getContent() in getContent to get the content
    #  of a crosslinked topic
    # receives an answerDict and returns a list of anki notes containing
    # one note for each question following this answerDict
    def getQuestionListForAnswer(self, answerDict: dict):

        # get all nodes following the answer in answerDict, including those
        # following a potential crosslink
        # if answerDict['crosslink']:
        #     crosslinkTopic = getTopicById(tId=answerDict['crosslink'],
        #                                   soup=self.soup, doc=self.doc)
        #     questions = crosslinkTopic.getSubTopics()
        #     if crosslinkNote:
        #         print('hier')
        potentialQuestions = answerDict['subTopic'].getSubTopics()
        # iterate through all questions
        questionList = []
        for potentialQuestion in potentialQuestions:
            if not (isEmptyNode(potentialQuestion)):
                questionList.append(potentialQuestion)
            else:
                nextAnswerDicts = self.findAnswerDicts(potentialQuestion)
                # code in brackets is for unlisting:
                # https://stackoverflow.com/a/952952
                followingQuestions = [item for sublist in
                                      self.getNextQuestions(nextAnswerDicts) for
                                      item in sublist]
                questionList.extend(followingQuestions)
        return questionList

    # sets the deck, fields and tag of an xmind note and adds it to the
    # collection
    def getNoteDict(self, sortId, question, answerDicts, ref, nextQuestions):
        # Set deck
        # note.model()['did'] = self.currentSheetImport['deckId']
        noteDict = dict(rf='', qt='', an=dict(), id='', mt='', tag='')

        # set field ID
        noteDict['id'] = sortId

        # Set field Question
        noteDict['qt'] = self.getContent(question)

        # Set Answer fields
        aId = 0
        for answerDict in answerDicts:
            if answerDict['isAnswer']:
                aId += 1
                noteDict['an']['a' + str(aId)] = self.getContent(
                    answerDict['subTopic'])
                answerDict['aId'] = str(aId)

        # Set field Reference
        noteDict['rf'] = '<ul>%s</ul>' % ref

        # set field Meta
        meta = self.getXMindMeta(question=question, nextQuestions=nextQuestions,
                                 answerDicts=answerDicts)
        noteDict['mt'] = meta

        # Set tag
        noteDict['tag'] = self.currentSheetImport['tag']

        return noteDict

    # receives a question node and returns a list of dictionaries containing the
    # subtopics, whether the subtopics contain an answer or not and whether they
    # contain a crosslink or not
    def findAnswerDicts(self, question: TopicElement):
        answerDicts = list()
        for subTopic in question.getSubTopics():
            # Check whether subtopic is not empty
            isAnswer = True
            if isEmptyNode(subTopic):
                isAnswer = False
            # Check whether subtopic contains a crosslink
            hasCrosslink = False
            href = subTopic.getHyperlink()
            if href and href.startswith('xmind:#'):
                hasCrosslink = True
            answerDicts.append(
                dict(subTopic=subTopic, isAnswer=isAnswer, aId=str(0),
                     hasCrosslink=hasCrosslink))
        actualAnswers = list(filter(
            lambda answerDict: answerDict['isAnswer'], answerDicts))
        if len(actualAnswers) > X_MAX_ANSWERS:
            self.running = False
            self.log = ["""Warning:
A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than %s Answers and try again.""" %
                        (question.getTitle(), X_MAX_ANSWERS, X_MAX_ANSWERS)]
        return answerDicts

    def noteFromNoteDict(self, noteDict):
        note = self.col.newNote()
        note.model()['did'] = self.deckId
        note.fields[list(X_FLDS.keys()).index('id')] = noteDict['id']
        note.fields[list(X_FLDS.keys()).index('qt')] = noteDict['qt']
        for key in noteDict['an']:
            note.fields[list(X_FLDS.keys()).index(key)] = noteDict['an'][key]
        note.fields[list(X_FLDS.keys()).index('rf')] = noteDict['rf']
        note.fields[list(X_FLDS.keys()).index('mt')] = noteDict['mt']
        note.tags.append(noteDict['tag'])

        return note
