import json
import os
import shutil
import tempfile

import bs4
from consts import X_MODEL_NAME, X_MAX_ANSWERS, X_FLDS
from deckselectiondialog import DeckSelectionDialog
from statusmanager import StatusManager
from utils import getCoordsFromId, getNotesFromSheet
from xmanager import getNodeCrosslink, get_child_nodes, is_empty_node, XManager, get_parent_topic
from xnotemanager import XNoteManager, FieldTranslator, update_sort_id, ref_plus_question, field_from_content, \
    ref_plus_answer
from xontology import get_rel_dict, get_question_sets, XOntology

import aqt
from anki.importing.noteimp import NoteImporter
from anki.utils import intTime, guid64, timestampID, splitFields, joinFields

# TODO: adjust sheet selection windows to adjust to the window size
# TODO: check out hierarchical tags, may be useful
# TODO: add warning when something is wrong with the map
# TODO: Implement hints as part of the meta json instead of javascript and use
#  sound=False to mute answers in hint
# TODO: Implement warning if an audio file can't be found
# TODO: Check for performance issues:
#  https://stackoverflow.com/questions/7370801/measure-time-elapsed-in-python
#  https://docs.python.org/3.6/library/profile.html
IMPORT_CANCELED_MESSAGE = 'Import canceled'


def get_xmind_meta(note_data):
    xmind_meta = dict()
    xmind_meta['path'] = note_data['document']
    xmind_meta['sheetId'] = note_data['sheetId']
    xmind_meta['questionId'] = note_data['questionId']
    answers = [a for a in note_data['answers'] if len(a) != 0]
    xmind_meta['answers'] = [{'answerId': a['src'],
                              'crosslink': a['crosslink'],
                              'children': a['children']} for a in answers]
    xmind_meta['nAnswers'] = len(answers)
    xmind_meta['subjects'] = note_data['subjects']
    return json.dumps(xmind_meta)


class XmindImporter(NoteImporter):
    """
    Importer for Xmind files. You can add this class to anki.importing.Importers list to add it to ankis importers.
    """
    needMapper = False

    def __init__(self, col, file, status_manager=None):
        NoteImporter.__init__(self, col, file)
        self.added_relations = {'storids': [], 'q_ids': []}
        self.model = col.models.byName(X_MODEL_NAME)
        self.mw = aqt.mw
        self.media_dir = os.path.join(os.path.dirname(col.path), 'collection.media')
        self.source_dir = tempfile.mkdtemp()
        self.warnings = []
        self.deck_id = ''
        self.deck_name = ''
        self.tags = dict()
        self.images = []
        self.media = []
        self.running = True
        self.repair = False
        self.active_manager = None
        self.note_manager = XNoteManager(col=self.col)
        self.current_sheet_import = ''
        self.onto = None
        self.translator = FieldTranslator()
        if not status_manager:
            self.status_manager = StatusManager()
        else:
            self.status_manager = status_manager
        self.last_nid = 0
        self.x_managers = [XManager(os.path.normpath(file))]
        self._register_referenced_x_managers(self.x_managers[0])

    def add_media(self):
        for manager in self.x_managers:
            for file in [f for f in self.media if f['doc'] == manager._file]:
                if file['identifier'].startswith(('attachments', 'resources')):
                    file_path = manager.getAttachment(identifier=file[
                        'identifier'], directory=self.source_dir)
                    self.col.media.addFile(file_path)
                else:
                    self.col.media.addFile(file['identifier'])
            for image in [i for i in self.images if i['doc'] == manager._file]:
                file_path = manager.getAttachment(identifier=image[
                    'identifier'], directory=self.source_dir)
                self.col.media.addFile(file_path)
        self.media = []
        self.images = []

    def addNew(self, notes):
        for note in notes:
            self.col.addNote(note)

    def import_edge(self, q_index, q_tag):
        # Update the sorting ID
        next_sort_id = update_sort_id(previousId=sort_id, idToAppend=q_index)
        content = self.active_manager.get_node_content(q_tag)
        answer_dicts = self.find_answer_dicts(
            parents=parent_a_dict['concepts'], question=q_tag,
            sort_id=next_sort_id, ref=ref, content=content)
        if answer_dicts:
            actual_answers = [a for a in answer_dicts if a['isAnswer']]
            is_question = not is_empty_node(q_tag)

            # If the current relation is a question and has too many
            # answers give a warning and stop running
            if is_question and len(actual_answers) > X_MAX_ANSWERS:
                self.running = False
                self.log = ["""Warning:
                        A Question titled "%s" has more than %s answers. Make sure every Question in your Map is 
                        followed by no more than %s Answers and try again.""" %
                            (self.active_manager.get_node_title(q_tag),
                             X_MAX_ANSWERS, X_MAX_ANSWERS)]
                return
            next_ref = ref_plus_question(
                field=field_from_content(content), ref=ref)
            for aId, answerDict in enumerate(answer_dicts, start=1):
                self.import_node_if_concept(
                    parent_answer_dict=answerDict, ref=next_ref,
                    sort_id=update_sort_id(
                        previousId=next_sort_id, idToAppend=aId),
                    follows_bridge=not is_question)

    def find_answer_dicts(self, parents, question, sort_id, ref, content):
        answer_dicts = list()
        manager = self.active_manager
        crosslink = getNodeCrosslink(question)
        child_notes = get_child_nodes(question)

        if len(child_notes) == 0:
            return self.stop_or_add_cross_question(
                content=content, crosslink=crosslink, manager=manager,
                parents=parents, question=question, ref=ref, sort_id=sort_id)

        # Convert the node content into a string that can be used as a
        # class-name
        question_class = self.translator.class_from_content(content)

        # Add a Child relation if the node is a bridge
        if not question_class:
            question_class = 'Child'

        image = content['media']['image']
        media = content['media']['media']
        bridges, children = self.get_children_and_bridges(
            answer_dicts, child_notes, image, media, parents, question, ref,
            question_class, sort_id)
        if len(children) > 0:

            # Assign all children to bridge concepts because they are the
            # subject of questions following bridges
            for bridge in bridges:
                bridge['concepts'] = children

        return answer_dicts

    def finish_import(self):
        # Add all notes to the collection
        if not self.running:
            return
        self.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'],
                    ['removed', 0, 'notes']]
        self.import_ontology()
        self.update_status()
        self.onto.save_changes()
        self.added_relations = {'storids': [], 'q_ids': []}
        for logId, log in enumerate(self.log, start=0):
            if log[1] == 1:
                self.log[logId][2] = 'note'
            self.log[logId][1] = str(self.log[logId][1])

        self.log = [
            ", ".join(list(map(lambda l: " ".join(l), self.log)))]
        if self.mw:
            self.mw.progress.finish()

        # Remove temp dir and its files
        shutil.rmtree(self.source_dir)

    def get_children_and_bridges(self, answer_dicts, child_notes, image, media,
                                 parents, question, ref, question_class,
                                 sort_id):
        children = list()
        bridges = list()
        a_index = 1
        sheet = self.active_manager.sheets[
            self.current_sheet_import]['tag']['id']
        doc = self.active_manager.file
        tag = self.get_tag()
        x_id = question['id']
        rel_prop = None
        for childNode in child_notes:
            answer_dict = self.get_answer_dict(node_tag=childNode, question=x_id)

            # Only add relations to answers that are concepts (not to empty
            # answers that serve as bridges for questions following multiple
            # answers)
            if answer_dict['isAnswer']:
                child = answer_dict['concepts'][0]
                children.append(child)
                for parent in parents:
                    rel_dict = get_rel_dict(
                        aIndex=a_index, image=image, media=media, x_id=x_id,
                        ref=ref, sortId=sort_id, doc=doc, sheet=sheet, tag=tag)
                    rel_prop = self.onto.add_relation(
                        child=child, class_text=question_class, parent=parent,
                        rel_dict=rel_dict)
                a_index += 1
            else:
                bridges.append(answer_dict)
            answer_dicts.append(answer_dict)
        if rel_prop:
            self.added_relations['storids'].append(rel_prop.storid)
            self.added_relations['q_ids'].append(x_id)
        return bridges, children

    def get_file_dict(self, path):
        return [path, self.active_manager.file]

    def import_node_if_concept(self, node: bs4.Tag, root=False):
        """
        If it is not empty, imports the node represented by the specified tag as a concept into the ontology and as
        a node into the smr world.
        :param node: the tag representing the node to import
        :param root: whether or not the concept to import is the root of the respective map
        """
        # If the node is empty do not create a concept
        if not is_empty_node(node):
            node_content = self.active_manager.get_node_content(node)
            concept = self.onto.add_concept(node_content=node_content, root=root)
            self.mw.smr_world.add_xmind_node(node=node, node_content=node_content, ontology_storid=concept.storid)

        following_relationships = get_child_nodes(node)
        for question_index, following_relationship in enumerate(following_relationships, start=1):
            self.import_edge(q_index=question_index, q_tag=following_relationship)

    def _register_referenced_x_managers(self, x_manager):
        """
        Adds XManagers referenced by ref sheet to xManagers list
        :param x_manager: the XManager to get References from
        """
        ref_managers = [XManager(f) for f in x_manager.get_referenced_files()]
        self.x_managers.extend(ref_managers)
        for manager in ref_managers:
            self._register_referenced_x_managers(manager)

    def get_tag(self):
        return (self.deck_name + '_' + self.current_sheet_import).replace(" ", "_")

    def import_ontology(self):
        triples = [self.onto.getElements(t) for t in self.onto.getNoteTriples() if
                   t[1] in self.added_relations['storids']]
        triples_with_q_ids = [self.onto.q_id_elements(t) for t in triples]
        added_triples = [t for t in triples_with_q_ids if t['q_id'] in self.added_relations['q_ids']]
        question_list = get_question_sets(added_triples)
        notes = [self.note_from_question_list(q) for q in question_list]
        self.addNew(notes=notes)
        self.add_media()

    def initialize_import(self, repair):
        """
        Sets up the required fields for the import and initializes the import
        :param repair: Whether or not the import is supposed to repair already once imported notes after the xmind
        node ids have changed, e.g. due to opening the map in a different program like xmind zen
        """
        self.deck_name = self.col.decks.get(self.deck_id)['name']
        self.repair = repair
        self.onto = XOntology(self.deck_id)
        # Set model to Stepwise map retrieval model
        self.col.decks.select(self.deck_id)
        self.col.decks.current()['mid'] = self.col.models.byName(X_MODEL_NAME)['id']
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        for manager in self.x_managers:
            self.import_file(manager)
        self.finish_import()

    def note_from_question_list(self, question_list):
        note = self.col.newNote()
        if note.id <= self.last_nid:
            note.id = self.last_nid + 1
        self.last_nid = note.id
        note.model()['did'] = self.deck_id
        note_data = self.onto.getNoteData(question_list)
        self.images.extend(note_data['images'])
        self.media.extend(note_data['media'])
        meta = get_xmind_meta(note_data)
        fields = [note_data['reference'],
                  note_data['question']]
        fields.extend([a['text'] if len(a) != 0 else '' for
                       a in note_data['answers']])
        fields.extend([note_data['sortId'], meta])
        note.fields = fields
        note.tags.append(note_data['tag'])
        return note

    def partial_import(self, seed_topic, sheet_id, deck_id, parent_q,
                       parent_as, onto=None):
        """
        Imports questions starting at a given point
        :param onto: Optional, Ontology to set as importer's ontology:
        :param seed_topic: Tag of the topic of the question to start at
        :param sheet_id: Xmind id of the sheet the question belongs to
        :param deck_id: Deck-id of the deck to import to
        :param parent_q: Tag of the parent-question of the question the
        import starts at
        :param parent_as: List of tags of the answers to the parent-question
        """
        self.set_up_import(deck_id=deck_id, sheet=sheet_id, onto=onto)
        self.col.decks.select(self.deck_id)
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
        parent_a_dict = self.get_answer_dict(
            node_tag=node_tag, question=parent_q['id'], root=False,
            a_concept=a_concept)

        # If the seed_topic's parent follows a bridge, start importing at the
        # bridge instead
        parent_q_children = get_child_nodes(parent_q)
        if get_parent_topic(seed_topic) not in parent_q_children:
            if len(parent_as) > 1:
                seed_topic = next(
                    g for c in parent_q_children if is_empty_node(c) for
                    g in get_child_nodes(c) if seed_topic.text in g.text)
            else:
                seed_topic = next(t for t in get_child_nodes(parent_as[0]) if
                                  seed_topic.text in t.text)
        ref, sort_id = self.active_manager.ref_and_sort_id(q_topic=seed_topic)
        q_index = sum(1 for _ in seed_topic.previous_siblings) + 1
        self.import_edge(
            sort_id=sort_id, q_index=q_index, q_tag=seed_topic,
            parent_a_dict=parent_a_dict, ref=ref)

    def run(self):
        """
        Starts deck selection dialog and runs import sheets with selected sheets
        """
        self.mw.progress.finish()
        # check whether the file has already been imported before
        if self.mw.smr_world.graph.execute("select * from xmind_files where path = '{seed_path}'".format(
                seed_path=self.file)).fetchone():
            self.log = ["It seems like {seed_path} is already in your collection. Please choose a different "
                        "file.".format(seed_path=self.file)]
            return
        deck_selection_dialog = DeckSelectionDialog(os.path.basename(self.x_managers[0]._file))
        deck_selection_dialog.exec_()
        user_inputs = deck_selection_dialog.get_inputs()
        if not user_inputs['running']:
            self.log = [IMPORT_CANCELED_MESSAGE]
            return
        self.deck_id = user_inputs['deckId']
        self.initialize_import(repair=user_inputs['repair'])

    def set_up_import(self, deck_id, sheet, onto=None):
        self.current_sheet_import = next(
            s for m in self.x_managers for
            s in m._sheets if m._sheets[s]['tag']['id'] == sheet)
        self.active_manager = next(
            m for m in self.x_managers for
            s in m._sheets if s == self.current_sheet_import)
        self.deck_id = deck_id
        if onto:
            self.onto = onto
        else:
            self.onto = XOntology(deck_id)
        self.deck_name = self.col.decks.get(self.deck_id)['name']

    def stop_or_add_cross_question(self, content, crosslink, manager, parents,
                                   question, ref, sort_id):

        # Stop and warn if no nodes follow the question
        if not crosslink:
            self.running = False
            self.log = ["""Warning:
                        A Question titled "%s" (Path %s) is missing answers. Please adjust your 
                        Concept Map and try again.""" % (
                manager.get_node_content(tag=question)[0],
                getCoordsFromId(sort_id))]
            return

        # If the question contains a crosslink, add another relation
        # from the parents of this question to the answers to the original
        # question
        else:
            original_question = manager.get_tag_by_id(crosslink)
            self.find_answer_dicts(parents=parents, question=original_question,
                                   sort_id=sort_id, ref=ref, content=content)
            return

    def note_from_note_data(self, note_data):
        note = self.col.newNote()
        note.model()['did'] = self.deck_id
        fields = splitFields(note_data[6])
        note.fields = fields
        note.tags.append(note_data[5].replace(" ", ""))
        return note

    def maybe_sync(self, sheet_id, note_list):
        if self.repair:
            # noinspection PyTypeChecker
            existing_notes = list(self.col.db.execute(
                "select id, flds from notes where tags like '%" +
                self.current_sheet_import['tag'].replace(" ", "") + "%'"))
        else:
            existing_notes = getNotesFromSheet(sheetId=sheet_id, col=self.col)
        if existing_notes:
            notes_2_add = []
            notes_2_update = []
            old_q_id_list = list(map(lambda n: json.loads(
                splitFields(n[1])[list(X_FLDS.keys()).index('mt')])[
                'questionId'], existing_notes))
            for newNote in note_list:
                new_fields = splitFields(newNote[6])
                new_meta = json.loads(new_fields[list(X_FLDS.keys()).index('mt')])
                new_q_id = new_meta['questionId']
                try:
                    if self.repair:
                        new_qt_x_aw = joinFields(new_fields[1:22])
                        old_tpl = tuple(
                            filter(lambda n: new_qt_x_aw in n[1], existing_notes))[0]
                        note_id = existing_notes.index(old_tpl)
                    else:
                        note_id = old_q_id_list.index(new_q_id)
                        # if the fields are different, add it to notes to be updated
                    if not existing_notes[note_id][1] == newNote[6]:
                        notes_2_update.append(
                            [existing_notes[note_id], newNote])
                    del existing_notes[note_id]
                    del old_q_id_list[note_id]
                except (ValueError, IndexError):
                    notes_2_add.append(newNote)
            self.addNew(notes_2_add)
            self.log[0][1] += len(notes_2_add)
            self.addUpdates(notes_2_update)
            self.log[1][1] += len(notes_2_update)
            self.removeOld(existing_notes)
            self.log[2][1] += len(existing_notes)
            self.col.save()
        else:
            notes_2_add = note_list
            self.addNew(notes_2_add)
            self.log[0][1] += len(notes_2_add)

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
    update cards set type = ?, queue = ?, due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?, left = ?, odue = ?, 
    flags = ? where nid = ? and ord = ?""",
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
        for manager in self.x_managers:
            remote = manager.get_remote()
            local = self.note_manager.get_local(manager._file)
            status = deep_merge(remote=remote, local=local)
            self.status_manager.add_new(status)
        self.status_manager.save()

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
        meta = get_xmind_meta(question=question, answerDicts=answerDicts,
                              siblings=siblings, connections=connections)
        noteList.append(meta)

        nId = timestampID(self.col.db, "notes")
        noteData = [nId, guid64(), self.model['id'], intTime(), self.col.usn(),
                    self.current_sheet_import['tag'], joinFields(noteList), "",
                    "", 0, ""]

        return noteData, media

    def import_file(self, x_manager: XManager):
        """
        Imports a file managed by the provided XManager and starts imports for all sheets in that file that contain
        concept maps
        :param x_manager: the x_manager that manages the file
        """
        self.active_manager = x_manager
        self.mw.smr_world.add_xmind_file(x_manager=x_manager, deck_id=self.deck_id)
        for sheet in x_manager.get_content_sheets():
            self.import_sheet(sheet)

    def import_sheet(self, sheet: str):
        """
        Imports the specified sheet and starts importing the map contained in that sheet starting from the root concept
        :param sheet: name of the sheet to be imported
        :return: adds the roottopic of the active sheet to self.onto and starts
                the map import by calling getQuestions
        """
        self.current_sheet_import = sheet
        self.mw.progress.update(label='importing %s' % sheet, maybeShow=False)
        self.mw.app.processEvents()
        self.mw.smr_world.add_xmind_sheet(x_manager=self.active_manager, sheet=sheet)
        root_node = self.active_manager.get_root_node(sheet=sheet)
        self.import_node_if_concept(node=root_node, root=True)
