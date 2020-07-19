import json
import os
import shutil
import tempfile
from typing import List, Dict, Optional

import bs4
from consts import X_MODEL_NAME, X_MAX_ANSWERS, X_FLDS
from deckselectiondialog import DeckSelectionDialog
from owlready2 import ThingClass
from statusmanager import StatusManager
from utils import get_edge_coordinates_from_parent_node, getNotesFromSheet
from xmanager import get_child_nodes, is_empty_node, XManager, get_parent_node, get_non_empty_sibling_nodes, \
    get_node_content, get_node_title
from xnotemanager import XNoteManager, FieldTranslator
from xontology import get_question_sets, XOntology

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
from aqt.main import AnkiQt

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
        self.added_relations: Dict[str, List] = {'storids': [], 'q_ids': []}
        self.model: Dict = col.models.byName(X_MODEL_NAME)
        self.mw: AnkiQt = aqt.mw
        self.media_dir: str = os.path.join(os.path.dirname(col.path), 'collection.media')
        self.source_dir: str = tempfile.mkdtemp()
        self.warnings: List[str] = []
        self.deck_id: str = ''
        self.deck_name: str = ''
        self.images: List = []
        self.media: List = []
        self.running: bool = True
        self.repair: bool = False
        self.active_manager: Optional[XManager] = None
        self.note_manager: XNoteManager = XNoteManager(col=self.col)
        self.current_sheet_import: str = ''
        self.onto: Optional[XOntology] = None
        self.translator: FieldTranslator = FieldTranslator()
        if not status_manager:
            self.status_manager: StatusManager = StatusManager()
        else:
            self.status_manager: StatusManager = status_manager
        self.last_nid: int = 0
        self.x_managers: List[XManager] = [XManager(os.path.normpath(file))]
        self._register_referenced_x_managers(self.x_managers[0])

    def add_media(self):
        for manager in self.x_managers:
            for file in [f for f in self.media if f['doc'] == manager._file]:
                if file['identifier'].startswith(('attachments', 'resources')):
                    file_path = manager.get_attachment(identifier=file[
                        'identifier'], directory=self.source_dir)
                    self.col.media.addFile(file_path)
                else:
                    self.col.media.addFile(file['identifier'])
            for image in [i for i in self.images if i['doc'] == manager._file]:
                file_path = manager.get_attachment(identifier=image[
                    'identifier'], directory=self.source_dir)
                self.col.media.addFile(file_path)
        self.media = []
        self.images = []

    def addNew(self, notes):
        for note in notes:
            self.col.addNote(note)

    def import_edge(self, order_number: int, edge: bs4.Tag, parent_node_ids: List[str],
                    parent_concepts: List[ThingClass]) -> None:
        """
        Creates concepts for all child nodes following the edge represented by the specified tag. Then adds the edge to
        the smr world and then calls import_node_if_concept() for all child nodes following the edge.
        :param order_number: order number of the edge with respect to its siblings
        :param edge: tag that represents the edge to be imported
        :param parent_node_ids: list of xmind ids of parent nodes
        :param parent_concepts: list of concepts of parent nodes
        """
        edge_content: Dict = get_node_content(edge)
        child_nodes: List[bs4.Tag] = get_child_nodes(edge)
        # stop execution and warn if an edge is not followed by any nodes
        if len(child_nodes) == 0:
            self.running = False
            self.log = [
                "Warning:\nA Question titled {title} (path {path}) is missing answers. Please adjust your Concept Map "
                "and try again.".format(
                    title=edge_content['content'], path=get_edge_coordinates_from_parent_node(
                        order_number=order_number, parent_node_ids=parent_node_ids[0]))]
            return
        # split the child nodes into two lists with empty and non empty child nodes to differentiate between them
        # when importing the triples
        non_empty_child_nodes = []
        empty_child_nodes = []
        for n in child_nodes:
            if is_empty_node(n):
                empty_child_nodes.append(n)
            else:
                non_empty_child_nodes.append(n)
        # If the current relation is a question and has too many answers give a warning and stop running
        if not is_empty_node(edge) and len(non_empty_child_nodes) > X_MAX_ANSWERS:
            self.running = False
            self.log = [
                "Warning:\nA Question titled \"{title}\" has more than {n_answers} answers. Make sure every Question "
                "in your Map is followed by no more than {n_answers} Answers and try again.".format(
                    title=get_node_title(edge), n_answers=X_MAX_ANSWERS)]
            return
        # create the concepts for the next iteration beforehand to be able to assign a list of all sibling concepts
        # to empty nodes for creating relationships following multiple concepts
        node_contents = [get_node_content(n) for n in non_empty_child_nodes]
        all_child_concepts = [self.onto.concept_from_node_content(node_content=n, node_is_root=False) for n in
                              node_contents]
        single_child_concepts = [[concept] for concept in all_child_concepts]
        # add the edge to the smr world
        self.mw.smr_world.add_xmind_edge(
            edge=edge, edge_content=edge_content, sheet_id=self.active_manager.get_sheet_id(self.current_sheet_import),
            order_number=order_number)
        # set the relationship class name for following triple imports
        relationship_class_name: str = self.translator.class_from_content(edge_content)
        if not relationship_class_name:
            relationship_class_name = 'Child'
        # import each child_node either with a list of the single concept or a list of all concepts if they are empty
        for order_number, (child_node, child_concepts) in enumerate(
                zip(non_empty_child_nodes + empty_child_nodes,
                    single_child_concepts + len(empty_child_nodes) * [all_child_concepts]), start=1):
            self.import_node_if_concept(
                node=child_node, concepts=child_concepts, parent_node_ids=parent_node_ids,
                parent_concepts=parent_concepts, parent_relationship_class_name=relationship_class_name,
                order_number=order_number)

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

    def get_file_dict(self, path):
        return [path, self.active_manager.file]

    def import_node_if_concept(
            self, node: bs4.Tag, concepts: List[ThingClass], parent_node_ids: Optional[List[str]] = None,
            parent_concepts: Optional[List[ThingClass]] = None, parent_edge_id: Optional[str] = None,
            parent_relationship_class_name: Optional[str] = None, order_number: int = 1) -> None:
        """
        If it is not empty, imports the node represented by the specified tag as a concept into the ontology and as
        a node into the smr world. Calls import_triple() for each parent node preceding the parent edge and
        import_edge() for each edge following the concept.
        :param node: the tag representing the node to import
        :param concepts:
        :param parent_node_ids: list of xmind ids of parent nodes for the triples that are imported for this node
        :param parent_concepts: list of concepts of parent nodes for creating the ontology relationships for this node
        :param parent_edge_id: xmind id of the node's parent edge
        :param parent_relationship_class_name: class name for the relationship in the triple that we import into the ontology
        :param order_number: order number of the node with respect to its siblings
        """
        if parent_node_ids is None:
            parent_node_ids = []
        if parent_concepts is None:
            parent_concepts = []
        following_relationships = get_child_nodes(node)
        if not is_empty_node(node):
            self.mw.smr_world.add_xmind_node(
                node=node, node_content=get_node_content(node), ontology_storid=concepts[0].storid,
                sheet_id=self.active_manager.get_sheet_id(self.current_sheet_import), order_number=order_number)
            for parent_node_id, parent_concept in zip(parent_node_ids, parent_concepts):
                self.import_triple(parent_node_id=parent_node_id, parent_thing='', edge_id=parent_edge_id,
                                   child_node_id=node['id'],
                                   relationship_class_name=parent_relationship_class_name)
            node_ids_preceding_next_edge: List[str] = [node['id']]
        else:
            node_ids_preceding_next_edge: List[str] = [n['id'] for n in get_non_empty_sibling_nodes(node)]
        for order_number, following_relationship in enumerate(following_relationships, start=1):
            self.import_edge(order_number=order_number, edge=following_relationship,
                             parent_node_ids=node_ids_preceding_next_edge, parent_concepts=concepts)

    def _register_referenced_x_managers(self, x_manager: XManager):
        """
        Adds XManagers referenced by ref sheet to xManagers list
        :param x_manager: the XManager to get References from
        """
        ref_managers: List[XManager] = [XManager(f) for f in x_manager.get_referenced_files()]
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
        if get_parent_node(seed_topic) not in parent_q_children:
            if len(parent_as) > 1:
                seed_topic = next(
                    g for c in parent_q_children if is_empty_node(c) for
                    g in get_child_nodes(c) if seed_topic.text in g.text)
            else:
                seed_topic = next(t for t in get_child_nodes(parent_as[0]) if
                                  seed_topic.text in t.text)
        ref, sort_id = self.active_manager.ref_and_sort_id(q_topic=seed_topic)
        q_index = sum(1 for _ in seed_topic.previous_siblings) + 1
        self.import_edge(order_number=q_index, edge=seed_topic)

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
        self.import_node_if_concept(node=root_node, node_is_root=True)

    def import_triple(self, parent_node_id: str, parent_thing: ThingClass, edge_id: str, child_node_id: str,
                      child_thing: ThingClass, relationship_class_name: str):
        self.onto.add_relation(child_thing=child_thing, relationship_class_name=relationship_class_name,
                               parent_thing=parent_thing)
        self.mw.smr_world.add_smr_triple()
