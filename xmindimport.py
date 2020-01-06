import json
import shutil
import owlready2
import types

from time import sleep

from anki.importing.noteimp import NoteImporter
from anki.utils import splitFields, joinFields, intTime, guid64, timestampID

from .sheetselectors import *
from .utils import *
from .consts import *
from .xmanager import XManager


# TODO: adjust sheet selection windows to adjust to the window size
# TODO: check out hierarchical tags, may be useful
# TODO: add warning when something is wrong with the map
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
        self.mw = aqt.mw
        self.mediaDir = os.path.join(os.path.dirname(col.path),
                                     'collection.media')
        self.srcDir = tempfile.mkdtemp()
        self.warnings = []
        self.deckId = ''
        self.tags = dict()
        self.running = True
        self.repair = False
        self.xManagers = [XManager(file)]
        self.activeManager = None
        self.currentSheetImport = ''
        # set up ontology
        self.onto = owlready2.get_ontology(
            os.path.join(ADDON_PATH, 'resources', 'onto.owl'))
        with self.onto:
            class Concept(owlready2.Thing):
                pass

            class Root(Concept):
                pass

            # standard object properties
            class Parent(Concept >> Concept):
                pass

            class Child(Concept >> Concept):
                inverse_property = Parent
                pass

            # Annotation properties for Concepts
            class Image(owlready2.AnnotationProperty):
                pass

            class Media(owlready2.AnnotationProperty):
                pass

            class Xid(owlready2.AnnotationProperty):
                pass

            # Annotation properties for relation triples
            class Reference(owlready2.AnnotationProperty):
                pass

    def findAnswerDicts(self, parent, question, sortId, ref, content):
        """
        :param question: question tag to get the answers for
        :return: list of dictionaries created with getAnswerDict()
        """
        answerDicts = list()
        manager = self.activeManager
        # stop and warn if no nodes follow the question
        crosslink = manager.getNodeCrosslink(question)
        childNotes = manager.getChildnodes(question)
        if len(childNotes) == 0 and not crosslink:
            self.running = False
            self.log = ["""Warning:
                    A Question titled "%s" (Path %s) is missing answers. Please adjust your 
                    Concept Map and try again.""" % (
                manager.getNodeContent(tag=question)[0],
                getCoordsFromId(sortId))]
            return
        # add relations to the ontology
        else:
            title = content['content']
            if not title:
                objProp = self.onto.Child
                title = 'Child'
            else:
                with self.onto:
                    objProp = types.new_class(title,
                                              (owlready2.ObjectProperty,))
                    objProp.domain = [self.onto.Concept]
                    objProp.range = [self.onto.Concept]
                    objProp.inverse_property = self.onto.Parent
            image = content['media']['image']
            media = content['media']['media']
            children = list()
            for childNode in childNotes:
                answerDict = self.getAnswerDict(childNode)
                child = answerDict['concept']
                children.append(child)
                self.onto.Reference[parent, objProp, child] = ref
                if image:
                    self.onto.Image[parent, objProp, child] = image
                if media:
                    self.onto.Media[parent, objProp, child] = media
                answerDicts.append(answerDict)
            setattr(parent, title, children)
            return answerDicts

    def getAnswerDict(self, nodeTag, root=False):
        """
        :param nodeTag: The answer node to get the dict for
        :param root: whether the node is the root or not
        :return: dictionary containing information for creating a note from
        this answer node, furthermore adds a Concept to onto for this node
        """
        # Check whether subtopic is not empty
        manager = self.activeManager
        isAnswer = True
        concept = None
        if manager.isEmptyNode(nodeTag):
            isAnswer = False
        else:
            nodeContent = manager.getNodeContent(nodeTag)
            if root:
                concept = self.onto.Root(nodeContent['content'])
            else:
                concept = self.onto.Concept(nodeContent['content'])
            concept.Image = nodeContent['media']['image']
            concept.Media = nodeContent['media']['media']
            concept.Xid = nodeTag['id']
        # Check whether subtopic contains a crosslink
        crosslink = manager.getNodeCrosslink(nodeTag)
        # Todo: check whether aID is really necessary
        return dict(nodeTag=nodeTag, isAnswer=isAnswer, aId=str(0),
                    crosslink=crosslink, concept=concept)

    def getQuestions(self, answerDict: dict, sortId='',
                     answerContent='', ref="", followsBridge=False):
        """
        :param answerDict: parent answer node of the questions to get
        :param sortId: current id for sortId field
        :param answerContent: content of parent answer in parent anki note
        :param ref: current text for reference field
        :param followsBridge: ???
        :return: creates notes for each question following the answerDict
        """
        manager = self.activeManager
        # The reference doesn't have to be edited at the roottopic
        if not isinstance(answerDict['concept'], self.onto.Root):
            # if the answerdict contains nothing (i.e. questions
            # following multiple answers), just close the reference
            if self.activeManager.isEmptyNode(
                    answerDict['nodeTag']) or followsBridge:
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + answerContent + '</li>'
        followRels = manager.getChildnodes(answerDict['nodeTag'])
        for qId, followRel in enumerate(followRels, start=1):
            # Update the sorting ID
            nextSortId = updateId(previousId=sortId, idToAppend=qId)
            # self.addXNote(parent=answerDict['concept'], question=followRel,
            #               ref=ref, sortId=nextSortId)
            content = manager.getNodeContent(followRel)
            answerDicts = self.findAnswerDicts(parent=answerDict['concept'],
                                               question=followRel,
                                               sortId=nextSortId, ref=ref,
                                               content=content)
            # if the current relation is a question and has more then 20
            # answers give a warning and stop running
            actualAnswers = list(filter(lambda a: a['isAnswer'], answerDicts))
            isQuestion = not manager.isEmptyNode(followRel)
            if isQuestion and len(actualAnswers) > X_MAX_ANSWERS:
                self.running = False
                self.log = ["""Warning:
            A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than %s Answers and try again.""" %
                            (manager.getNodeTitle(followRel),
                             X_MAX_ANSWERS, X_MAX_ANSWERS)]
                return
            # update ref with content of this question but without sound
            refContent = replaceSound(content['content'])
            ref = ref + '<li>' + refContent
            for aId, answerDict in enumerate(answerDicts, start=1):
                if manager.getChildnodes(answerDict['nodeTag']):
                    if answerDict['isAnswer']:
                        ac = splitFields(noteData[6])[
                            list(X_FLDS.keys()).index('a' + answerDict['aId'])]
                        answerContent = replaceSound(ac)
                    else:
                        answerContent = ''
                    self.getQuestions(answerDict=answerDict,
                                      answerContent=answerContent, ref=ref,
                                      sortId=updateId(previousId=sortId,
                                                      idToAppend=aId))

    def getValidSheets(self):
        """
        :return: sheets of all xManagers with concept maps to import
        """
        sheets = list()
        for manager in self.xManagers:
            validSheets = filter(lambda k: k != 'ref',
                                 list(manager.sheets.keys()))
            sheets.extend(validSheets)
        return sheets

    def getRefManagers(self, xManager):
        """
        :param xManager: the xManager to get References from
        :return: adds xManagers referenced by ref sheet to xManagers list
        """
        for key in xManager.sheets:
            sheet = xManager.sheets[key]
            # get reference sheets
            if sheet('title', recursive=False)[0].text == 'ref':
                ref_tags = getChildnodes(sheet.topic)
                ref_paths = map(xManager.getNodeHyperlink, ref_tags)
                for path in filter(lambda ref_path: ref_path is not None,
                                   ref_paths):
                    clean_path = path.replace('file://', '')
                    clean_path = clean_path.replace('%20', ' ')
                    clean_path = clean_path.split('/')
                    clean_path[0] = clean_path[0] + '\\'
                    clean_path = os.path.join(*clean_path)
                    ref_xManager = XManager(clean_path)
                    self.xManagers.append(ref_xManager)
                    self.getRefManagers(ref_xManager)

    def importMap(self):
        """
        :return: adds the roottopic of the active sheet to self.onto and starts
            the map import by calling getQuestions
        """
        manager = self.activeManager
        rootTopic = manager.sheets[self.currentSheetImport].topic
        # Set model to Stepwise map retrieval model
        xModel = self.col.models.byName(X_MODEL_NAME)
        self.col.decks.select(self.deckId)
        self.col.decks.current()['mid'] = xModel['id']
        rootDict = self.getAnswerDict(nodeTag=rootTopic, root=True)
        self.getQuestions(answerDict=rootDict,
                          ref=manager.getNodeTitle(rootTopic))

    def importSheets(self, selectedSheets):
        """
        :param selectedSheets: sheets that were selected by the user in
            Selector Dialog
        :return: Imports maps in all sheets contained in selectedSheets
        """
        for manager in self.xManagers:
            self.activeManager = manager
            validSheets = filter(lambda s: s in selectedSheets, manager.sheets)
            for sheet in validSheets:
                self.currentSheetImport = sheet
                self.mw.progress.update(label='importing %s' % sheet['tag'],
                                        maybeShow=False)
                self.mw.app.processEvents()
                self.importMap()
        # add all notes to the collection
        if not self.running:
            return
        self.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'],
                    ['removed', 0, 'notes']]
        # get content of fields for the note to add for this question
        # code from addxnotes, probably necessary here
        # self.addMedia(media)
        # noteData, media = self.getNoteData(sortId=sortId,
        #                                    question=question,
        #                                    answerDicts=answerDicts,
        #                                    ref=ref,
        #                                    siblings=siblings,
        #                                    connections=connections)
        #
        for sheetId, noteList in self.notesToAdd.items():
            self.maybeSync(sheetId=sheetId, noteList=noteList)
        for logId, log in enumerate(self.log, start=0):
            if log[1] == 1:
                self.log[logId][2] = 'note'
            self.log[logId][1] = str(self.log[logId][1])

        self.log = [
            ", ".join(list(map(lambda l: " ".join(l), self.log)))]
        self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
        print("fertig")

    def run(self):
        """
        :return: starts sheetselector dialog and runs import sheets with
            selected sheets
        """
        self.getRefManagers(self.xManagers[0])
        sheets = self.getValidSheets()
        if len(sheets) > 1:
            selector = MultiSheetSelector(sheets)
        else:
            selector = SingleSheetSelector(sheets)
        self.mw.progress.finish()
        selector.exec_()
        userInputs = selector.getInputs()
        if not userInputs['running']:
            self.log = ['Import canceled']
            return
        selectedSheets = userInputs['selectedSheets']
        self.deckId = userInputs['deckId']
        self.repair = userInputs['repair']
        self.tags = userInputs['tags']
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        self.importSheets(selectedSheets)

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
        xMindMeta['lastSync'] = intTime()
        return json.dumps(xMindMeta)

    def addAttachment(self, attachment):
        # extract attachment to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.addFile(srcPath)

    def getNextQuestions(self, answerDicts: list, addCrosslinks=True,
                         goDeeper=True):
        """receives a list of answerDicts and returns a list of anki notes for each subtopic"""

        nextQuestions = []
        globalQuestions = []
        bridges = list(filter(lambda answerDict: not answerDict['isAnswer'],
                              answerDicts))
        answers = list(filter(lambda answerDict: answerDict['isAnswer'],
                              answerDicts))
        # TODO: globalQUestions add connections as global questions check whtether thats true
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
                if crosslink and isQuestionNode(
                        getTagById(self.tagList, crosslink)):
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
            crosslinkAnswerDict = self.getAnswerDict(crosslinkNode)
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

        nId = timestampID(self.col.db, "notes")
        noteData = [nId, guid64(), self.model['id'], intTime(), self.col.usn(),
                    self.currentSheetImport['tag'], joinFields(noteList), "",
                    "", 0, ""]

        return noteData, media

    def noteFromNoteData(self, noteData):
        note = self.col.newNote()
        note.model()['did'] = self.deckId
        fields = splitFields(noteData[6])
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
                    self.col.media.addFile(files['media'])

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
                splitFields(n[1])[list(X_FLDS.keys()).index('mt')])[
                'questionId'], existingNotes))
            for newNote in noteList:
                newFields = splitFields(newNote[6])
                newMeta = json.loads(newFields[list(X_FLDS.keys()).index('mt')])
                newQId = newMeta['questionId']
                try:
                    if self.repair:
                        print('')
                        newQtxAw = joinFields(newFields[1:22])
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
        self.col.remNotes(oldIds)

    def addUpdates(self, rows):
        for noteTpl in rows:
            fields = []
            # get List of aIds to check whether the cards for this note have
            # changed
            fields.append(splitFields(noteTpl[0][1]))
            fields.append(splitFields(noteTpl[1][6]))
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
        for noteData in rows:
            self.col.addNote(self.noteFromNoteData(noteData))
            sleep(0.001)
