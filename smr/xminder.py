import json
from pathlib import Path
from time import sleep
from typing import List

import aqt
from anki.importing.noteimp import NoteImporter, ADD_MODE
from anki.utils import split_fields, join_fields, int_time, guid64, timestamp_id

from .dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from .utils import *
from .consts import *


class XmindImporter(NoteImporter):
    needMapper = False

    def __init__(self, col, file):
        NoteImporter.__init__(self, col, file)
        self.model = col.models.by_name(X_MODEL_NAME)
        self.sheets = None
        self.mw = aqt.mw
        self.currentSheetImport = {}
        self.mediaDir = os.path.join(os.path.dirname(col.path),
                                     'collection.media')
        self.srcDir = tempfile.mkdtemp()
        self.xZip = zipfile.ZipFile(file, 'r')
        self.warnings = []
        self.deckId = ''
        self.notesToAdd = dict()
        self.running = True
        self.soup = BeautifulSoup(self.xZip.read('content.xml'), features='html.parser')
        self.tagList = self.soup('topic')
        self.repair = False
        # Fields to make methods from super class work
        self.needMapper: bool = True
        self.mapping: List[str] = list(X_FLDS.values())
        self.updateCount: int = 0
        self.importMode: int = ADD_MODE

    def importSheets(self, user_inputs: DeckSelectionDialogUserInputsDTO):
        self.deckId = user_inputs.deck_id
        self.repair = user_inputs.repair
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        sheet = self.soup('sheet')[0]
        tag = f'{user_inputs.deck_name}::{sheet.title.text.replace(" ", "_")}'
        self.currentSheetImport = {
            'sheet': sheet,
            'tag': tag,
            'deckId': user_inputs.deck_id,
        }
        self.currentSheetImport['ID'] = self.currentSheetImport['sheet']['id']
        self.notesToAdd[self.currentSheetImport['ID']] = list()
        self.mw.progress.update(label=f'importing {tag}', maybeShow=False)
        self.mw.app.processEvents()
        self.importMap(self.currentSheetImport)
        # add all notes to the collection
        if not self.running:
            self.mw.progress.finish()
            return
        self.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'],
                    ['removed', 0, 'notes']]
        for sheetId, noteList in self.notesToAdd.items():
            self.maybeSync(sheetId=sheetId, noteList=noteList)
        for logId, log in enumerate(self.log, start=0):
            if log[1] == 1:
                self.log[logId][2] = 'note'
            self.log[logId][1] = str(self.log[logId][1])

        self.log = [
            ", ".join(list(map(lambda l: " ".join(l), self.log)))]
        self.mw.reset()
        self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)

    def importMap(self, sheetImport: dict):
        rootTopic = sheetImport['sheet'].topic
        # Set model to Stepwise map retrieval model
        xModel = self.col.models.by_name(X_MODEL_NAME)
        self.col.decks.select(self.currentSheetImport['deckId'])
        self.col.decks.current()['mid'] = xModel['id']
        rootDict = getAnswerDict(rootTopic)
        self.getQuestions(answerDict=rootDict, ref=getNodeTitle(rootTopic))

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
        if not answerDict['nodeTag'].previous_element.name == 'sheet':
            # if the answerdict contains nothing (i.e. questions
            # following multiple answers), just close the reference
            if isEmptyNode(answerDict['nodeTag']) or followsBridge:
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + answerContent + '</li>'
        questionDicts = self.findQuestionDicts(answer=answerDict['nodeTag'],
                                               ref=ref, sortId=sortId)
        siblingQuestions = self.getQuestionListForAnswer(answerDict)
        for qId, questionDict in enumerate(questionDicts, start=1):
            # Update the sorting ID
            nextSortId = updateId(previousId=sortId, idToAppend=qId)
            if self.running:
                # if the current question serves as a bridge to serve as
                # reference, do not get any notes for this bridge but for
                # questions following its answers
                if questionDict['isBridge']:
                    answerDicts = self.findAnswerDicts(questionDict['nodeTag'])
                    for aId, answerDict in enumerate(answerDicts, start=1):
                        if getChildnodes(answerDict['nodeTag']):
                            if answerDict['isAnswer']:
                                answerContent, media = getNodeContent(
                                    tagList=self.tagList,
                                    tag=answerDict['nodeTag'])
                                self.addMedia([media])
                                answerContent = replaceSound(answerContent)
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
                # if this is a regular question
                else:
                    siblings = list(map(lambda s: s['qId'], filter(
                        lambda q: (q['qId'] != questionDict[
                            'nodeTag']['id']) and not q['isConnection'],
                        siblingQuestions)))
                    connections = list(map(lambda s: s['qId'], filter(
                        lambda q: (q['qId'] != questionDict[
                            'nodeTag']['id']) and q['isConnection'],
                        siblingQuestions)))
                    self.addXNote(question=questionDict['nodeTag'],
                                  ref=questionDict['ref'], sortId=nextSortId,
                                  siblings=siblings, connections=connections)

    # creates a noteDict for this question, and
    # recursively calls getQuestions() to add notes following this question
    # Inputs:
    # question: xmind question node
    # ref: current reference text
    # qId: position of the question node relative to its siblings
    # note: note to be added for the question node
    def addXNote(self, question, ref, sortId, siblings=None,
                 connections=None):
        answerDicts = self.findAnswerDicts(question)
        actualAnswers = list(filter(
            lambda a: a['isAnswer'], answerDicts))
        if len(actualAnswers) > X_MAX_ANSWERS:
            self.running = False
            self.log = ["""Warning:
A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than %s Answers and try again.""" %
                        (getNodeTitle(question),
                         X_MAX_ANSWERS, X_MAX_ANSWERS)]
            return None

        if not self.running:
            self.log = ["""Warning:
An answer to the question "%s" (path: %s) contains a hyperlink to a deleted node. Please adjust your Concept Map and try again.""" %
                        (getNodeContent(tagList=self.tagList, tag=question)[
                             0], getCoordsFromId(sortId))]
            return None

        # get content of fields for the note to add for this question
        noteData, media = self.getNoteData(sortId=sortId,
                                           question=question,
                                           answerDicts=answerDicts,
                                           ref=ref,
                                           siblings=siblings,
                                           connections=connections)
        self.addMedia(media)

        # add to list of notes to add
        self.notesToAdd[self.currentSheetImport['ID']].append(noteData)

        # add notes for questions following this note
        questionContent = replaceSound(
            split_fields(noteData[6])[list(X_FLDS.keys()).index('qt')])
        ref = ref + '<li>' + questionContent
        for aId, answerDict in enumerate(answerDicts, start=1):
            if getChildnodes(answerDict['nodeTag']):
                if answerDict['isAnswer']:
                    ac = split_fields(noteData[6])[
                        list(X_FLDS.keys()).index('a' + answerDict['aId'])]
                    answerContent = replaceSound(ac)
                else:
                    answerContent = ''
                self.getQuestions(answerDict=answerDict,
                                  answerContent=answerContent, ref=ref,
                                  sortId=updateId(previousId=sortId,
                                                  idToAppend=aId))

            # receives a question, sheet and list of notes possibly following each
            # answer to this question and returns a json file

    def getXMindMeta(self, question, answerDicts, siblings,
                     connections):
        xMindMeta = dict()
        xMindMeta['path'] = self.file
        xMindMeta['sheetId'] = self.currentSheetImport['sheet']['id']
        xMindMeta['questionId'] = question['id']
        xMindMeta['answers'] = []
        answers = list(filter(lambda answerDict: answerDict['isAnswer'],
                              answerDicts))

        # get questions following each answer
        nextQuestions = self.getNextQuestions(answerDicts)
        for aId, answer in enumerate(answers, start=0):
            # write each answer and its following questions into meta
            xMindMeta['answers'].append(dict())
            xMindMeta['answers'][aId]['answerId'] = answer[
                'nodeTag']['id']
            xMindMeta['answers'][aId]['children'] = []
            for question in nextQuestions[aId]:
                xMindMeta['answers'][aId]['children'].append(
                    question['qId'])
        xMindMeta['nAnswers'] = len(answers)
        xMindMeta['siblings'] = siblings
        xMindMeta['connections'] = connections
        xMindMeta['lastSync'] = int_time()
        return json.dumps(xMindMeta)

    def addAttachment(self, attachment):
        # extract attachment to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.add_file(srcPath)

    def getNextQuestions(self, answerDicts: list, addCrosslinks=True,
                         goDeeper=True):
        """receives a list of answerDicts and returns a list of anki notes for each subtopic"""

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
        potentialQuestions = getChildnodes(answerDict['nodeTag'])
        # iterate through all questions
        questionList = []
        for potentialQuestion in potentialQuestions:
            if not (isEmptyNode(potentialQuestion)):
                # If this question contains a crosslink to another question
                crosslink = getNodeCrosslink(potentialQuestion)
                if crosslink and isQuestionNode(getTagById(self.tagList, crosslink)):
                    questionList.append(
                        dict(qId=crosslink, isConnection=not addCrosslinks))
                else:
                    questionList.append(dict(qId=potentialQuestion['id'],
                                             isConnection=not addCrosslinks))
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
            crosslinkNode = getTagById(tagList=self.tagList,
                                       tagId=answerDict['crosslink'])
            if not crosslinkNode:
                self.running = False
                return None
            crosslinkAnswerDict = getAnswerDict(crosslinkNode)
            # Do not add crosslinks following crosslinks to avoid endless loops
            crosslinkQuestions = self.getQuestionListForAnswer(
                answerDict=crosslinkAnswerDict, addCrosslinks=False)
            questionList.extend(crosslinkQuestions)
        return questionList

    def getNoteData(self, sortId, question, answerDicts, ref, siblings,
                    connections):
        """returns a list of all content needed to create the a new note and
        the media contained in that note in a list"""

        noteList = []
        media = []

        # Set field Reference
        noteList.append('<ul>%s</ul>' % ref)

        # Set field Question
        qtContent, qtMedia = getNodeContent(tagList=self.tagList, tag=question)
        noteList.append(qtContent)
        media.append(qtMedia)

        # Set Answer fields
        aId = 0
        for answerDict in answerDicts:
            if answerDict['isAnswer']:
                aId += 1
                # noinspection PyTypeChecker
                anContent, anMedia = getNodeContent(tagList=self.tagList,
                                                    tag=answerDict['nodeTag'])
                noteList.append(anContent)
                media.append(anMedia)
                answerDict['aId'] = str(aId)

        # noinspection PyShadowingNames
        for i in range(aId, X_MAX_ANSWERS):
            noteList.append('')

        # set field ID
        noteList.append(sortId)

        # set field Meta
        meta = self.getXMindMeta(question=question, answerDicts=answerDicts,
                                 siblings=siblings, connections=connections)
        noteList.append(meta)

        nId = timestamp_id(self.col.db, "notes")
        noteData = [nId, guid64(), self.model['id'], int_time(), self.col.usn(),
                    self.currentSheetImport['tag'], join_fields(noteList), "",
                    "", 0, ""]

        return noteData, media

    # receives a question node and returns a list of dictionaries containing the
    # subtopics, whether the subtopics contain an answer or not and whether they
    # contain a crosslink or not
    def findAnswerDicts(self, question):
        answerDicts = list()
        for childNode in getChildnodes(question):
            answerDict = getAnswerDict(childNode)
            answerDicts.append(answerDict)
        return answerDicts

    def noteFromNoteData(self, noteData):
        note = self.col.newNote()
        fields = split_fields(noteData[6])
        note.fields = fields
        note.tags.append(noteData[5].replace(" ", ""))
        return note

    def addMedia(self, media):
        for files in media:
            if files['image']:
                self.addAttachment(files['image'])
            if files['media']:
                if files['media'].startswith(('attachments', 'resources')):
                    self.addAttachment(files['media'])
                else:
                    self.col.media.add_file(Path(self.file).parent / files['media'])

    # receives an answer node and returns all questions following this answer
    # including questions following multiple topics as dictionaries of a
    # question node and its corresponding reference
    def findQuestionDicts(self, answer, sortId, ref=''):
        followRels = getChildnodes(answer)
        questionDicts = []
        for followRel in followRels:
            crosslink = getNodeCrosslink(followRel)
            if len(getChildnodes(followRel)) == 0:
                # stop and warn if no nodes follow the question
                if not crosslink:
                    self.running = False
                    self.log = ["""Warning:
A Question titled "%s" (Path %s) is missing answers. Please adjust your Concept Map and try again.""" %
                                (getNodeContent(tagList=self.tagList,
                                                tag=followRel)[0],
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
        return dict(nodeTag=subTopic, ref=ref, isBridge=isBridge,
                    crosslink=crosslink)

    def maybeSync(self, sheetId, noteList):
        if self.repair:
            existingNotes = list(self.col.db.execute(
                "select id, flds from notes where tags like '%" +
                self.currentSheetImport['tag'].replace(" ", "") + "%'"))
        else:
            existingNotes = getNotesFromSheet(sheetId=sheetId, col=self.col)
        if existingNotes:
            notesToAdd = []
            notesToUpdate = []
            oldQIdList = list(map(lambda n: json.loads(
                split_fields(n[1])[list(X_FLDS.keys()).index('mt')])[
                'questionId'], existingNotes))
            for newNote in noteList:
                newFields = split_fields(newNote[6])
                newMeta = json.loads(newFields[list(X_FLDS.keys()).index('mt')])
                newQId = newMeta['questionId']
                try:
                    if self.repair:
                        print('')
                        newQtxAw = join_fields(newFields[1:22])
                        oldTpl = tuple(
                            filter(lambda n: newQtxAw in n[1], existingNotes))[
                            0]
                        noteId = existingNotes.index(oldTpl)
                    else:
                        noteId = oldQIdList.index(newQId)
                        # if the fields are different, add it to notes to be updated
                    if not existingNotes[noteId][1] == newNote[6]:
                        notesToUpdate.append(
                            [existingNotes[noteId], newNote])
                    del existingNotes[noteId]
                    del oldQIdList[noteId]
                except (ValueError, IndexError):
                    notesToAdd.append(newNote)
            self.addNew(notesToAdd)
            self.log[0][1] += len(notesToAdd)
            self.addUpdates(notesToUpdate)
            self.log[1][1] += len(notesToUpdate)
            self.removeOld(existingNotes)
            self.log[2][1] += len(existingNotes)
            self.col.save()
        else:
            notesToAdd = noteList
            self.addNew(notesToAdd)
            self.log[0][1] += len(notesToAdd)

    def removeOld(self, existingNotes):
        oldIds = list(map(lambda nt: nt[0], existingNotes))
        self.col.remove_notes(oldIds)

    def addUpdates(self, rows):
        for noteTpl in rows:
            fields = []
            # get List of aIds to check whether the cards for this note have
            # changed
            fields.append(split_fields(noteTpl[0][1]))
            fields.append(split_fields(noteTpl[1][6]))
            metas = list(
                map(lambda f: json.loads(f[list(X_FLDS.keys()).index('mt')]),
                    fields))
            aIds = list(
                map(lambda m: list(map(lambda a: a['answerId'], m['answers'])),
                    metas))

            cardUpdates = []
            if not self.repair:
                # if answers have changed get data for updating their status
                if not aIds[0] == aIds[1]:
                    cardUpdates = self.getCardUpdates(aIds, noteTpl)

            # fix for missing spaces in tags
            noteTpl[1][5] = f' {noteTpl[1][5]} '
            # change contents of this note
            updateData = [noteTpl[1][3:7] + [noteTpl[0][0]]]
            self.col.db.executemany("""
            update notes set mod = ?, usn = ?, tags = ?,  flds = ?
            where id = ?""", updateData)

            if not self.repair:
                # change card values where necessary
                for CUId, cardUpdate in enumerate(cardUpdates, start=0):
                    if cardUpdate != '':
                        self.col.db.executemany("""
    update cards set type = ?, queue = ?, due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?, left = ?, odue = ?, flags = ? where nid = ? and ord = ?""",
                                                [list(cardUpdate) + [
                                                    str(noteTpl[0][0]),
                                                    str(CUId)]])

    def getCardUpdates(self, aIds, noteTpl):
        cardUpdates = []
        # Get relevant values of the prior answers
        relevantVals = ['type', 'queue', 'due', 'ivl', 'factor', 'reps',
                        'lapses', 'left', 'odue', 'flags']
        # remember prior values of cards that have moved
        oldVals = list(self.col.db.execute(
            "select " + ", ".join(relevantVals) + " from cards where nid = " +
            str(noteTpl[0][0])))
        for i, aId in enumerate(aIds[1], start=0):
            # if this answer was a different answer before, remember the
            # stats
            try:
                if aId != aIds[0][i]:
                    try:
                        cardUpdates.append(oldVals[aIds[0].index(aId)])
                    except ValueError:
                        # if this answer was not in the old answers at all
                        # get Values for a completely new card
                        cardUpdates.append([str(0)] * 10)
                else:
                    # if this answer was the same answer before, ignore it
                    cardUpdates.append('')
            except IndexError:
                # if this answer was not in the old answers at all
                # get Values for a completely new card
                cardUpdates.append([str(0)] * 10)
        return cardUpdates

    def addNew(self, rows):
        self.col.decks.select(self.deckId)

        deck = self.col.decks.get(self.deckId)
        deck['mid'] = self.model['id']
        self.col.decks.save(deck)

        self.model['did'] = self.deckId
        self.col.models.save(self.model)
        for noteData in rows:
            self.col.addNote(self.noteFromNoteData(noteData))
            sleep(0.001)
