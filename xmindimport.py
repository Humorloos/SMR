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
from .xontology import XOntology


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
        self.deckName = ''
        self.tags = dict()
        self.images = []
        self.media = []
        self.running = True
        self.repair = False
        self.xManagers = [XManager(file)]
        self.activeManager = None
        self.currentSheetImport = ''
        self.onto = XOntology()

    def addNew(self, notes):
        for note in notes:
            self.col.addNote(note)
            sleep(0.001)

    def findAnswerDicts(self, parents, question, sortId, ref, content):
        """
        :param question: question tag to get the answers for
        :return: list of dictionaries created with getAnswerDict()
        """
        answerDicts = list()
        manager = self.activeManager
        crosslink = manager.getNodeCrosslink(question)
        childNotes = manager.getChildnodes(question)
        if len(childNotes) == 0:
            # stop and warn if no nodes follow the question
            if not crosslink:
                self.running = False
                self.log = ["""Warning:
                        A Question titled "%s" (Path %s) is missing answers. Please adjust your 
                        Concept Map and try again.""" % (
                    manager.getNodeContent(tag=question)[0],
                    getCoordsFromId(sortId))]
                return
            # if the question contains a crosslink, add another relation
            # from the parents of this question to the answers to the original
            # question
            else:
                originalQuestion = manager.getTagById(crosslink)
                self.findAnswerDicts(parents=parents,
                                     question=originalQuestion,
                                     sortId=sortId, ref=ref,
                                     content=content)
                return
        # add relations to the ontology
        else:
            relTitle = classify(content['content'])
            if not relTitle:
                relProp = self.onto.Child
                relTitle = 'Child'
            else:
                with self.onto:
                    relProp = types.new_class(relTitle,
                                              (owlready2.ObjectProperty,))
                    relProp.domain = [self.onto.Concept]
                    relProp.range = [self.onto.Concept]
            image = content['media']['image']
            media = content['media']['media']
            children = list()
            bridges = list()
            for childNode in childNotes:
                answerDict = self.getAnswerDict(childNode)
                if answerDict['isAnswer']:
                    child = answerDict['concepts'][0]
                    children.append(child)
                    for parent in parents:
                        self.onto.Reference[parent, relProp, child] = ref
                        if sortId:
                            self.onto.SortId[parent, relProp, child] = sortId
                        self.onto.Doc[parent, relProp, child] = \
                            self.activeManager.file
                        self.onto.Sheet[parent, relProp, child] = \
                            self.activeManager.sheets[
                                self.currentSheetImport]['id']
                        self.onto.Xid[parent, relProp, child] = question['id']
                        if image:
                            self.onto.Image[parent, relProp, child] = image
                        if media:
                            self.onto.Media[parent, relProp, child] = media
                        self.onto.NoteTag[parent, relProp, child] = \
                            self.getTag()
                else:
                    bridges.append(answerDict)
                answerDicts.append(answerDict)
            if len(children) > 0:
                for bridge in bridges:
                    bridge['concepts'] = children
                for parent in parents:
                    setattr(parent, relTitle, children)
                for child in children:
                    setattr(child, 'Parent', parents)
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
                try:
                    concept = self.onto.Concept(nodeContent['content'])
                except TypeError:
                    print('fehler')
                    raise NameError('Invalid concept name')

            concept.Image = nodeContent['media']['image']
            concept.Media = nodeContent['media']['media']
            # Do not add an Xid if the node is a pure crosslink-node
            if manager.getNodeTitle(nodeTag) or manager.getNodeImg(nodeTag) \
                    or not manager.getNodeCrosslink(nodeTag):
                concept.Xid.append(nodeTag['id'])
            concept = [concept]
        # Check whether subtopic contains a crosslink
        crosslink = manager.getNodeCrosslink(nodeTag)
        # Todo: check whether aID is really necessary
        return dict(nodeTag=nodeTag, isAnswer=isAnswer, aId=str(0),
                    crosslink=crosslink, concepts=concept)

    def getQuestions(self, parentAnswerDict: dict, sortId='', ref="",
                     followsBridge=False):
        """
        :param parentAnswerDict: parent answer node of the questions to get
        :param sortId: current id for sortId field
        :param ref: current text for reference field
        :param followsBridge: ???
        :return: creates notes for each question following the answerDict
        """
        manager = self.activeManager
        answerContent = manager.getNodeContent(parentAnswerDict['nodeTag'])[
            'content']
        # The reference doesn't have to be edited at the roottopic
        if not isinstance(parentAnswerDict['concepts'][0], self.onto.Root):
            # if the answerdict contains nothing (i.e. questions
            # following multiple answers), just close the reference
            if not parentAnswerDict['isAnswer']:
                ref = ref + '</li>'
            else:
                ref = ref + ': ' + replaceSound(answerContent) + '</li>'
        followRels = manager.getChildnodes(parentAnswerDict['nodeTag'])
        for qId, followRel in enumerate(followRels, start=1):
            # Update the sorting ID
            nextSortId = updateId(previousId=sortId, idToAppend=qId)
            content = manager.getNodeContent(followRel)
            if content['content'] == 'difference to MAO':
                print('')
            answerDicts = self.findAnswerDicts(
                parents=parentAnswerDict['concepts'], question=followRel,
                sortId=nextSortId, ref=ref, content=content)
            if answerDicts:
                # if the current relation is a question and has more then 20
                # answers give a warning and stop running
                actualAnswers = [a for a in answerDicts if a['isAnswer']]
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
                nextRef = ref + '<li>' + refContent
                for aId, answerDict in enumerate(answerDicts, start=1):
                    if manager.getChildnodes(parentAnswerDict['nodeTag']):
                        self.getQuestions(parentAnswerDict=answerDict,
                                          ref=nextRef,
                                          sortId=updateId(previousId=nextSortId,
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
                ref_tags = xManager.getChildnodes(sheet.topic)
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

    def getTag(self):
        return " " + (self.deckName + '_' + self.currentSheetImport).replace(
            " ", "_") + " "

    def getXMindMeta(self, noteData):
        xMindMeta = dict()
        xMindMeta['path'] = noteData['document']
        xMindMeta['sheetId'] = noteData['sheetId']
        xMindMeta['questionId'] = noteData['questionId']
        answers = [a for a in noteData['answers'] if len(a) != 0]
        xMindMeta['answers'] = [{'answerId': a['id'],
                                 'children': a['children']} for a in answers]
        xMindMeta['nAnswers'] = len(answers)
        xMindMeta['subjects'] = noteData['subjects']
        xMindMeta['lastSync'] = intTime()
        return json.dumps(xMindMeta)

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
        self.getQuestions(parentAnswerDict=rootDict,
                          ref=manager.getNodeTitle(rootTopic))

    def importOntology(self):
        triples = self.onto.getNoteTriples()
        # Sort triples by question id for Triples pertaining to the same
        # question to appear next to each other
        ascendingQId = sorted(triples, key=lambda t: self.onto.getXid(
            self.onto.getElements(t)))
        qIds = [self.onto.getXid(self.onto.getElements(t)) for t in
                ascendingQId]

        questionList = []
        tripleList = [ascendingQId[0]]  # Initiate tripleList with first triple
        for x, qId in enumerate(qIds[0:-1], start=1):
            # Add the triple to the questionList if the next triple has a
            # different question id
            if qId != qIds[x]:
                questionList.append(tripleList)
                tripleList = [ascendingQId[x]]
            # Add the triple to the tripleList if it pertains to the same
            # question as the next triple
            else:
                tripleList.append(ascendingQId[x])
        questionList.append(tripleList)

        notes = [self.noteFromQuestionList(q) for q in questionList]
        self.addNew(notes=notes)

    def importSheets(self, selectedSheets):
        """
        :param selectedSheets: sheets that were selected by the user in
            Selector Dialog
        :return: Imports maps in all sheets contained in selectedSheets
        """
        for manager in self.xManagers:
            self.activeManager = manager
            validSheets = [s for s in selectedSheets if s in manager.sheets]
            for sheet in validSheets:
                self.currentSheetImport = sheet
                self.mw.progress.update(label='importing %s' % sheet,
                                        maybeShow=False)
                self.mw.app.processEvents()
                self.importMap()
        # add all notes to the collection
        if not self.running:
            return
        self.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'],
                    ['removed', 0, 'notes']]
        self.importOntology()
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

    def noteFromQuestionList(self, questionList):
        note = self.col.newNote()
        note.model()['did'] = self.deckId
        noteData = self.onto.getNoteData(questionList)
        self.images.extend(noteData['images'])
        self.media.extend(noteData['media'])
        meta = self.getXMindMeta(noteData)
        fields = [noteData['reference'],
                  noteData['question']]
        fields.extend([a['text'] if len(a) != 0 else '' for
                       a in noteData['answers']])
        fields.extend([noteData['sortId'], meta])
        note.fields = fields
        note.tags.append(noteData['tag'])
        return note

    def run(self):
        """
        :return: starts sheetselector dialog and runs import sheets with
            selected sheets
        """
        self.getRefManagers(self.xManagers[0])
        sheets = self.getValidSheets()
        selector = SingleSheetSelector(os.path.basename(self.xManagers[0].file))
        self.mw.progress.finish()
        selector.exec_()
        userInputs = selector.getInputs()
        if not userInputs['running']:
            self.log = ['Import canceled']
            return
        self.deckId = userInputs['deckId']
        self.deckName = self.col.decks.get(self.deckId)['name']
        self.repair = userInputs['repair']
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        self.importSheets(sheets)

    def addAttachment(self, attachment):
        # extract attachment to anki media directory
        self.xZip.extract(attachment, self.srcDir)
        # get image from subdirectory attachments in mediaDir
        srcPath = os.path.join(self.srcDir, attachment)
        self.col.media.addFile(srcPath)

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

