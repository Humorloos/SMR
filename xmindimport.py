from anki.importing.noteimp import NoteImporter
from anki.utils import joinFields, intTime, guid64, timestampID
from .consts import *
from .sheetselectors import *
from .statusmanager import StatusManager
from .xmanager import *
from .xontology import *
from .utils import deep_merge


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
        self.added_relations = {'storids': [], 'q_ids': []}
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
        self.xManagers = [XManager(os.path.normpath(file))]
        self.activeManager = None
        self.noteManager = XNoteManager(col=self.col)
        self.currentSheetImport = ''
        self.onto = None
        self.statusManager = StatusManager()
        self.lastNid = 0

    def addMedia(self):
        for manager in self.xManagers:
            for file in [f for f in self.media if f['doc'] == manager.file]:
                if file['identifier'].startswith(('attachments', 'resources')):
                    file_path = manager.getAttachment(identifier=file[
                        'identifier'], directory=self.srcDir)
                    self.col.media.addFile(file_path)
                else:
                    self.col.media.addFile(file['identifier'])
            for image in [i for i in self.images if i['doc'] == manager.file]:
                file_path = manager.getAttachment(identifier=image[
                    'identifier'], directory=self.srcDir)
                self.col.media.addFile(file_path)

    def addNew(self, notes):
        for note in notes:
            self.col.addNote(note)

    def add_question(self, sort_id, q_index, q_tag, parent_a_dict, ref):
        # Update the sorting ID
        nextSortId = update_sort_id(previousId=sort_id, idToAppend=q_index)
        content = self.activeManager.getNodeContent(q_tag)
        answerDicts = self.findAnswerDicts(
            parents=parent_a_dict['concepts'], question=q_tag,
            sortId=nextSortId, ref=ref, content=content)
        if answerDicts:
            actualAnswers = [a for a in answerDicts if a['isAnswer']]
            isQuestion = not isEmptyNode(q_tag)

            # If the current relation is a question and has too many
            # answers give a warning and stop running
            if isQuestion and len(actualAnswers) > X_MAX_ANSWERS:
                self.running = False
                self.log = ["""Warning:
                        A Question titled "%s" has more than %s answers. Make sure every Question in your Map is followed by no more than %s Answers and try again.""" %
                            (self.activeManager.getNodeTitle(q_tag),
                             X_MAX_ANSWERS, X_MAX_ANSWERS)]
                return
            nextRef = ref_plus_question(
                field=field_from_content(content), ref=ref)
            for aId, answerDict in enumerate(answerDicts, start=1):
                if getChildnodes(parent_a_dict['nodeTag']):
                    self.getQuestions(
                        parentAnswerDict=answerDict, ref=nextRef,
                        sortId=update_sort_id(
                            previousId=nextSortId, idToAppend=aId),
                        followsBridge=not isQuestion)

    def findAnswerDicts(self, parents, question, sortId, ref, content):
        answerDicts = list()
        manager = self.activeManager
        crosslink = getNodeCrosslink(question)
        childNotes = getChildnodes(question)

        if len(childNotes) == 0:
            return self.stop_or_add_cross_question(
                content=content, crosslink=crosslink, manager=manager,
                parents=parents, question=question, ref=ref, sortId=sortId)

        # Convert the node content into a string that can be used as a
        # class-name
        question_class = classify(content)

        # Add a Child relation if the node is a bridge
        if not question_class:
            question_class = 'Child'

        image = content['media']['image']
        media = content['media']['media']
        bridges, children = self.get_children_and_bridges(
            answerDicts, childNotes, image, media, parents, question, ref,
            question_class, sortId)
        if len(children) > 0:

            # Assign all children to bridge concepts because they are the
            # subject of questions following bridges
            for bridge in bridges:
                bridge['concepts'] = children

        return answerDicts

    def finish_import(self):
        # Add all notes to the collection
        if not self.running:
            return
        self.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'],
                    ['removed', 0, 'notes']]
        self.importOntology()
        self.update_status()
        self.onto.save_changes()
        for logId, log in enumerate(self.log, start=0):
            if log[1] == 1:
                self.log[logId][2] = 'note'
            self.log[logId][1] = str(self.log[logId][1])

        self.log = [
            ", ".join(list(map(lambda l: " ".join(l), self.log)))]
        if self.mw:
            self.mw.progress.finish()
        # Remove temp dir and its files
        shutil.rmtree(self.srcDir)
        print("fertig")

    def getAnswerDict(self, nodeTag, question=None, root=False, a_concept=None):
        """
        :param question: Xmind id of the question the answer refers to
        :param nodeTag: The answer node to get the dict for
        :param root: whether the node is the root or not
        :return: dictionary containing information for creating a note from
        this answer node, furthermore adds a Concept to onto for this node
        """
        manager = self.activeManager
        isAnswer = True
        crosslink = None

        # If the node is empty do not create a concept
        if not nodeTag or isEmptyNode(nodeTag):
            isAnswer = False
        else:
            # Check whether subtopic contains a crosslink
            crosslink = getNodeCrosslink(nodeTag)
            if not a_concept:
                nodeContent = manager.getNodeContent(nodeTag)
                x_id = nodeTag['id']
                a_concept = self.onto.add_concept(
                    crosslink=crosslink, nodeContent=nodeContent, a_id=x_id,
                    root=root, file=self.activeManager.file, q_id=question)

                # Assign a list to concept since concept may also contain
                # multiple concepts in case of bridges
            a_concept = [a_concept]
        # Todo: check whether aID is really necessary
        return dict(nodeTag=nodeTag, isAnswer=isAnswer, aId=str(0),
                    crosslink=crosslink, concepts=a_concept)

    def get_children_and_bridges(self, answerDicts, childNotes, image, media,
                                 parents, question, ref, question_class,
                                 sortId):
        children = list()
        bridges = list()
        aIndex = 1
        sheet = self.activeManager.sheets[
            self.currentSheetImport]['tag']['id']
        doc = self.activeManager.file
        tag = self.getTag()
        x_id = question['id']
        rel_prop = None
        for childNode in childNotes:
            answerDict = self.getAnswerDict(nodeTag=childNode, question=x_id)

            # Only add relations to answers that are concepts (not to empty
            # answers that serve as bridges for questions following multiple
            # answers)
            if answerDict['isAnswer']:
                child = answerDict['concepts'][0]
                children.append(child)
                for parent in parents:
                    rel_dict = get_rel_dict(
                        aIndex=aIndex, image=image, media=media, x_id=x_id,
                        ref=ref, sortId=sortId, doc=doc, sheet=sheet, tag=tag)
                    rel_prop = self.onto.add_relation(
                        child=child, class_text=question_class, parent=parent,
                        rel_dict=rel_dict)
                aIndex += 1
            else:
                bridges.append(answerDict)
            answerDicts.append(answerDict)
        if rel_prop:
            self.added_relations['storids'].append(rel_prop.storid)
            self.added_relations['q_ids'].append(x_id)
        return bridges, children

    def get_file_dict(self, path):
        return [path, self.activeManager.file]

    def getQuestions(self, parentAnswerDict: dict, sortId='', ref="",
                     followsBridge=False):
        """
        :param parentAnswerDict: parent answer node of the questions to get
        :param sortId: current id for sortId field
        :param ref: current text for reference field
        :param followsBridge: ???
        :return: creates notes for each question following the answerDict
        """
        answerContent = self.activeManager.getNodeContent(
            parentAnswerDict['nodeTag'])['content']

        # The reference doesn't have to be edited at the roottopic
        if not isinstance(parentAnswerDict['concepts'][0], self.onto.Root):
            ref = ref_plus_answer(
                field=answerContent, followsBridge=followsBridge,
                ref=ref, mult_subjects=not parentAnswerDict['isAnswer'])
        followRels = getChildnodes(parentAnswerDict['nodeTag'])
        for qId, followRel in enumerate(followRels, start=1):
            self.add_question(sort_id=sortId, q_index=qId, q_tag=followRel,
                              parent_a_dict=parentAnswerDict, ref=ref)

    def getValidSheets(self):
        """
        :return: sheets of all xManagers with concept maps to import
        """
        sheets = list()
        for manager in self.xManagers:
            sheets.extend(manager.content_sheets())
        return sheets

    def getRefManagers(self, xManager):
        """
        :param xManager: the xManager to get References from
        :return: adds xManagers referenced by ref sheet to xManagers list
        """
        ref_managers = [XManager(f) for f in xManager.get_ref_files()]
        self.xManagers.extend(ref_managers)
        for manager in ref_managers:
            self.getRefManagers(manager)

    def getTag(self):
        return (self.deckName + '_' + self.currentSheetImport).replace(" ", "_")

    def getXMindMeta(self, noteData):
        xMindMeta = dict()
        xMindMeta['path'] = noteData['document']
        xMindMeta['sheetId'] = noteData['sheetId']
        xMindMeta['questionId'] = noteData['questionId']
        answers = [a for a in noteData['answers'] if len(a) != 0]
        xMindMeta['answers'] = [{'answerId': a['src'],
                                 'crosslink': a['crosslink'],
                                 'children': a['children']} for a in answers]
        xMindMeta['nAnswers'] = len(answers)
        xMindMeta['subjects'] = noteData['subjects']
        return json.dumps(xMindMeta)

    def importMap(self, sheet=None, deck_id=None):
        """
        :return: adds the roottopic of the active sheet to self.onto and starts
            the map import by calling getQuestions
        """
        if sheet:
            self.set_up_import(deck_id, sheet)
        manager = self.activeManager
        rootTopic = manager.sheets[self.currentSheetImport]['tag'].topic

        # Set model to Stepwise map retrieval model
        xModel = self.col.models.byName(X_MODEL_NAME)
        self.col.decks.select(self.deckId)
        self.col.decks.current()['mid'] = xModel['id']
        rootDict = self.getAnswerDict(nodeTag=rootTopic, root=True)
        self.getQuestions(parentAnswerDict=rootDict,
                          ref=manager.getNodeTitle(rootTopic))

    def importOntology(self):
        triples = [self.onto.getElements(t) for t in
                   self.onto.getNoteTriples() if t[1] in
                   self.added_relations['storids']]
        triples_with_q_ids = [self.onto.q_id_elements(t) for t in triples]
        added_triples = [t for t in triples_with_q_ids if t['q_id'] in
                         self.added_relations['q_ids']]
        questionList = get_question_sets(added_triples)

        notes = [self.noteFromQuestionList(q) for q in questionList]
        self.addNew(notes=notes)
        self.addMedia()

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
                if self.mw:
                    self.mw.progress.update(label='importing %s' % sheet,
                                            maybeShow=False)
                    self.mw.app.processEvents()
                self.importMap()
        self.finish_import()

    def init_import(self, deck_id, repair):
        sheets = self.getValidSheets()
        self.deckId = deck_id
        self.deckName = self.col.decks.get(self.deckId)['name']
        self.repair = repair
        self.onto = XOntology(deck_id)
        if self.mw:
            self.mw.progress.start(immediate=True, label='importing...')
            self.mw.app.processEvents()
            self.mw.checkpoint("Import")
        self.importSheets(sheets)

    def noteFromQuestionList(self, questionList):
        note = self.col.newNote()
        if note.id <= self.lastNid:
            note.id = self.lastNid + 1
        self.lastNid = note.id
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

    def partial_import(self, seed_topic, sheet_id, deck_id, parent_q,
                       parent_as):
        self.set_up_import(deck_id=deck_id, sheet=sheet_id)
        self.col.decks.select(self.deckId)
        self.col.decks.current()['mid'] = self.col.models.byName(
            X_MODEL_NAME)['id']
        parent_a_concepts = [self.onto.get_answer_by_a_id(
            a_id=a['id'], q_id=parent_q['id']) for a in parent_as]
        if len(parent_as) > 1:
            node_tag = None
            a_concept = parent_a_concepts
        else:
            node_tag = parent_as[0]
            a_concept = parent_a_concepts[0]
        parent_a_dict = self.getAnswerDict(
            nodeTag=node_tag, question=parent_q['id'], root=False,
            a_concept=a_concept)

        # If the seed_topic's parent follows a bridge, start importing at the
        # bridge instead
        parent_q_children = getChildnodes(parent_q)
        if get_parent_topic(seed_topic) not in parent_q_children:
            if len(parent_as) > 1:
                seed_topic = next(
                    g for c in parent_q_children if isEmptyNode(c) for
                    g in getChildnodes(c) if seed_topic.text in g.text)
            else:
                seed_topic = next(t for t in getChildnodes(parent_as[0]) if
                                  seed_topic.text in t.text)
        ref, sort_id = self.activeManager.ref_and_sort_id(q_topic=seed_topic)
        q_index = sum(1 for _ in seed_topic.previous_siblings) + 1
        self.add_question(
            sort_id=sort_id, q_index=q_index, q_tag=seed_topic,
            parent_a_dict=parent_a_dict, ref=ref)

    def run(self):
        """
        :return: starts sheetselector dialog and runs import sheets with
            selected sheets
        """
        self.getRefManagers(self.xManagers[0])
        selector = SingleSheetSelector(os.path.basename(self.xManagers[0].file))
        self.mw.progress.finish()
        selector.exec_()
        userInputs = selector.getInputs()
        if not userInputs['running']:
            self.log = ['Import canceled']
            return
        self.init_import(deck_id=userInputs['deckId'],
                         repair=userInputs['repair'])

    def set_up_import(self, deck_id, sheet):
        self.currentSheetImport = next(
            s for m in self.xManagers for
            s in m.sheets if m.sheets[s]['tag']['id'] == sheet)
        self.activeManager = next(
            m for m in self.xManagers for
            s in m.sheets if s == self.currentSheetImport)
        self.deckId = deck_id
        self.onto = XOntology(deck_id)
        self.deckName = self.col.decks.get(self.deckId)['name']

    def stop_or_add_cross_question(self, content, crosslink, manager, parents,
                                   question, ref, sortId):

        # Stop and warn if no nodes follow the question
        if not crosslink:
            self.running = False
            self.log = ["""Warning:
                        A Question titled "%s" (Path %s) is missing answers. Please adjust your 
                        Concept Map and try again.""" % (
                manager.getNodeContent(tag=question)[0],
                getCoordsFromId(sortId))]
            return

        # If the question contains a crosslink, add another relation
        # from the parents of this question to the answers to the original
        # question
        else:
            originalQuestion = manager.getTagById(crosslink)
            self.findAnswerDicts(parents=parents, question=originalQuestion,
                                 sortId=sortId, ref=ref, content=content)
            return

    def noteFromNoteData(self, noteData):
        note = self.col.newNote()
        note.model()['did'] = self.deckId
        fields = splitFields(noteData[6])
        note.fields = fields
        note.tags.append(noteData[5].replace(" ", ""))
        return note

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

    def update_status(self):
        for manager in self.xManagers:
            remote = manager.get_remote()
            local = self.noteManager.get_local(manager.file)
            status = deep_merge(remote=remote, local=local)
            self.statusManager.add_new(status)
        self.statusManager.save()

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
