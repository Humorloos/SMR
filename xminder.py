import json
import zipfile
import tempfile
import shutil
import urllib.parse

from time import sleep

from anki.importing.noteimp import NoteImporter

from .xmind.xxmind import load

from .sheetselectors import *
from .utils import *
from .consts import *


# TODO: add warning when something is wrong with the map
# TODO: add synchronization feature
# TODO: add new prestentation order
# In reviewer line 87 give getCard() the _note attribute and change getCard
# TODO: Implement hints as part of the meta json instead of javascript and use
#  sound=False to mute answers in hint
# TODO: Implement warning if an audio file can't be found
# TODO: Check for performance issues:
#  https://stackoverflow.com/questions/7370801/measure-time-elapsed-in-python
#  https://docs.python.org/3.6/library/profile.html
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
        rootDict = getAnswerDict(rootTopic)
        self.getQuestions(answerDict=rootDict, ref=rootTopic.getTitle())

    # calls createNotes for each answer.
    # Inputs:
    # answer: parent answer node of the questions to get
    # notes: list of notes for the notes to be created from the gotten questions
    # AnswerContent: content of parent answer in parent anki note
    # ref: current text for reference field
    # aId: current id for id field
    def getQuestions(self, answerDict: dict, sortId='',
                     answerContent='', ref="", followsBridge=False):
        # The reference doesn't have to be edited at the roottopic
        if not answerDict['subTopic'].getParentNode().tagName == 'sheet':
            # if the answerdict contains nothing (i.e. questions
            # following multiple answers), just close the reference
            if isEmptyNode(answerDict['subTopic']) or followsBridge:
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + answerContent + '</li>'
        questionDicts = self.findQuestionDicts(answer=answerDict['subTopic'],
                                               ref=ref, sortId=sortId)
        siblingQuestions = self.getQuestionListForAnswer(answerDict)
        for qId, questionDict in enumerate(questionDicts, start=1):
            # Update the sorting ID
            nextSortId = updateId(previousId=sortId, idToAppend=qId)
            if self.running:
                if questionDict['isBridge']:
                    answerDicts = self.findAnswerDicts(questionDict['subTopic'])
                    for aId, answerDict in enumerate(answerDicts, start=1):
                        if answerDict['subTopic'].getSubTopics():
                            if answerDict['isAnswer']:
                                answerContent = replaceSound(
                                    self.getContent(answerDict['subTopic'])[0])
                                newRef = ref + '<li>' + answerContent
                            else:
                                answerContent = ''
                                newRef = ref
                            self.getQuestions(answerDict=answerDict,
                                              answerContent=answerContent,
                                              ref=newRef,
                                              sortId=updateId(
                                                  previousId=nextSortId,
                                                  idToAppend=aId),
                                              followsBridge=True)
                else:
                    siblings = list(
                        filter(lambda q: q != questionDict['subTopic'].getID(),
                               siblingQuestions))
                    self.addXNote(question=questionDict['subTopic'],
                                  ref=questionDict['ref'], sortId=nextSortId,
                                  siblings=siblings)

                    # Inputs:
                    # question: xmind question node
                    # ref: current reference text
                    # qId: position of the question node relative to its siblings
                    # note: note to be added for the question node
                    # creates notes for the children of this note, configures this note and
                    # recursively calls getQuestions() to add notes following this note

    def addXNote(self, question: TopicElement, ref, sortId, siblings=None):

        answerDicts = self.findAnswerDicts(question)
        actualAnswers = list(filter(
            lambda a: a['isAnswer'], answerDicts))
        if len(actualAnswers) > X_MAX_ANSWERS:
            self.running = False
            self.log = ["""Warning:
A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than %s Answers and try again.""" %
                        (question.getTitle(), X_MAX_ANSWERS, X_MAX_ANSWERS)]
        if self.running:
            # Create Notes for next questions for Question nids in Meta field
            nextQuestions = self.getNextQuestions(answerDicts)

            # get content of fields for the note to add for this question
            noteDict, media = self.getNoteDict(sortId=sortId,
                                               question=question,
                                               answerDicts=answerDicts,
                                               ref=ref,
                                               nextQuestions=nextQuestions,
                                               siblings=siblings)
            self.addMedia(media)
            # add to list of notes to add
            self.notesToAdd.append(noteDict)

            # add notes for questions following this note
            questionContent = replaceSound(noteDict['qt'])
            ref = ref + '<li>' + questionContent
            for aId, answerDict in enumerate(answerDicts, start=1):
                if answerDict['subTopic'].getSubTopics():
                    if answerDict['isAnswer']:
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
                     answerDicts, siblings):
        xMindMeta = dict()
        xMindMeta['path'] = self.file
        xMindMeta['sheetId'] = self.currentSheetImport['sheet'].getID()
        xMindMeta['questionId'] = question.getID()
        xMindMeta['answers'] = []
        answers = list(filter(lambda answerDict: answerDict['isAnswer'],
                              answerDicts))
        for aId, answer in enumerate(answers, start=0):
            # write each answer and its following questions into meta
            xMindMeta['answers'].append(dict())
            xMindMeta['answers'][aId]['answerId'] = answer[
                'subTopic'].getID()
            xMindMeta['answers'][aId]['children'] = []
            for qId in nextQuestions[aId]:
                xMindMeta['answers'][aId]['children'].append(
                    qId)
        xMindMeta['nAnswers'] = len(answers)
        xMindMeta['siblings'] = siblings
        return json.dumps(xMindMeta)

    def addAttachment(self, attachment):
        # extract attachment to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.addFile(srcPath)

    # get the content of a node as string and add files to the collection if
    # necessary
    def getContent(self, node: TopicElement):
        content = ''
        media = dict(image=None, media=None)
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
            if content != '':
                content += '<br>'
            fileName = re.search('/.*', attachment).group()[1:]
            content += '<img src="%s">' % fileName
            media['image'] = attachment
        except:
            pass
        # if necessary add media file
        if href and href.endswith(('.mp3', '.wav', 'mp4')):
            if content != '':
                content += '<br>'
            if href.startswith('file'):
                mediaPath = urllib.parse.unquote(href[7:])
                media['media'] = mediaPath
            else:
                mediaPath = href[4:]
                media['media'] = mediaPath
                mediaPath = os.path.join(self.srcDir, mediaPath)
            content += '[sound:%s]' % os.path.basename(mediaPath)
        return content, media

    # receives a list of answerDicts and returns a list of anki notes for each
    # subtopic
    def getNextQuestions(self, answerDicts: list, addCrosslinks=True,
                         goDeeper=True):
        nextQuestions = []
        globalQuestions = []
        bridges = list(filter(lambda answerDict: not answerDict['isAnswer'],
                              answerDicts))
        answers = list(filter(lambda answerDict: answerDict['isAnswer'],
                              answerDicts))
        for bridge in bridges:
            globalQuestions.extend(self.getQuestionListForAnswer(bridge))
        for answer in answers:
            # Add one new note for each question following this subTopic
            questionListForAnswer = self.getQuestionListForAnswer(
                answerDict=answer, globalQuestions=globalQuestions,
                addCrosslinks=addCrosslinks, goDeeper=goDeeper)
            nextQuestions.append(questionListForAnswer)
        return nextQuestions

    # receives an answerDict and returns a list of xmind topic ids
    def getQuestionListForAnswer(self, answerDict: dict, globalQuestions=None,
                                 addCrosslinks=True, goDeeper=True):
        # get all nodes following the answer in answerDict, including those
        # following a potential crosslink
        potentialQuestions = answerDict['subTopic'].getSubTopics()
        # iterate through all questions
        questionList = []
        for potentialQuestion in potentialQuestions:
            if not (isEmptyNode(potentialQuestion)):
                crosslink = getCrosslink(potentialQuestion)
                if crosslink:
                    questionList.append(crosslink)
                else:
                    questionList.append(potentialQuestion.getID())
            else:
                if goDeeper:
                    nextAnswerDicts = self.findAnswerDicts(potentialQuestion)
                    # code in brackets is for unlisting:
                    # https://stackoverflow.com/a/952952
                    followingQuestions = [item for sublist in
                                          self.getNextQuestions(
                                              answerDicts=nextAnswerDicts,
                                              addCrosslinks=addCrosslinks,
                                              goDeeper=False) for
                                          item in sublist]
                    questionList.extend(followingQuestions)
        if globalQuestions:
            questionList.extend(globalQuestions)
        if answerDict['crosslink'] and addCrosslinks:
            crosslinkAnswerDict = getAnswerDict(
                getTopicById(tId=answerDict['crosslink'], importer=self))
            # Do not add crosslinks following crosslinks to avoid endless loops
            crosslinkQuestions = self.getQuestionListForAnswer(
                answerDict=crosslinkAnswerDict, addCrosslinks=False)
            questionList.extend(crosslinkQuestions)

        return questionList

    # sets the deck, fields and tag of an xmind note and adds it to the
    # collection
    def getNoteDict(self, sortId, question, answerDicts, ref, nextQuestions,
                    siblings):

        noteDict = dict(rf='', qt='', an=dict(), id='', mt='', tag='')
        media = []

        # set field ID
        noteDict['id'] = sortId

        # Set field Question
        noteDict['qt'], qtMedia = self.getContent(question)
        media.append(qtMedia)

        # Set Answer fields
        aId = 0
        for answerDict in answerDicts:
            if answerDict['isAnswer']:
                aId += 1
                # noinspection PyTypeChecker
                noteDict['an']['a' + str(aId)], anMedia = self.getContent(
                    answerDict['subTopic'])
                answerDict['aId'] = str(aId)
                media.append(anMedia)

        # Set field Reference
        noteDict['rf'] = '<ul>%s</ul>' % ref

        # set field Meta
        meta = self.getXMindMeta(question=question, nextQuestions=nextQuestions,
                                 answerDicts=answerDicts, siblings=siblings)
        noteDict['mt'] = meta

        # Set tag
        noteDict['tag'] = self.currentSheetImport['tag']

        return noteDict, media

    # receives a question node and returns a list of dictionaries containing the
    # subtopics, whether the subtopics contain an answer or not and whether they
    # contain a crosslink or not
    def findAnswerDicts(self, question: TopicElement):
        answerDicts = list()
        for subTopic in question.getSubTopics():
            answerDict = getAnswerDict(subTopic)
            answerDicts.append(answerDict)
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

    def addMedia(self, media):
        for files in media:
            if files['image']:
                self.addAttachment(files['image'])
            if files['media']:
                if files['media'].startswith(('attachments', 'resources')):
                    self.addAttachment(files['media'])
                else:
                    self.col.media.addFile(files['media'])

    # receives an answer node and returns all questions following this answer
    # including questions following multiple topics as dictionaries of a question
    # node and its corresponding reference
    def findQuestionDicts(self, answer: TopicElement, sortId, ref=''):
        followRels = answer.getSubTopics()
        questionDicts = []
        for followRel in followRels:
            crosslink = getCrosslink(followRel)
            if len(followRel.getSubTopics()) == 0:
                # stop and warn if no nodes follow the question
                if not crosslink:
                    self.running = False
                    self.log = ["""Warning:
A Question titled "%s" (Path %s) is missing answers. Please adjust your Concept Map and try again.""" %
                                (self.getContent(followRel)[0],
                                 getCoordsFromId(sortId))]
            else:
                questionDict = self.getQuestionDict(subTopic=followRel, ref=ref,
                                                    isBridge=False,
                                                    crosslink=crosslink)
                if isEmptyNode(followRel):
                    questionDict['isBridge'] = True

                questionDicts.append(questionDict)
        return questionDicts

    def getQuestionDict(self, subTopic, ref, isBridge, crosslink):
        return dict(subTopic=subTopic, ref=ref, isBridge=isBridge,
                    crosslink=crosslink)
