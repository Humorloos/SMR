import os
from typing import List, Optional

import bs4

import aqt
from anki.importing.noteimp import NoteImporter, ForeignNote, ForeignCard, ADD_MODE
from anki.models import NoteType
from anki.utils import joinFields
from aqt.main import AnkiQt
from main.consts import X_MODEL_NAME, X_MAX_ANSWERS, SMR_NOTE_FIELD_NAMES
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.dto.nodecontentdto import NodeContentDTO
from main.smrworld import SmrWorld
from main.utils import get_edge_coordinates_from_parent_node
from main.xmanager import get_child_nodes, is_empty_node, XManager, get_non_empty_sibling_nodes, \
    get_node_content, get_node_title
from main.xnotemanager import FieldTranslator, get_smr_note_reference_field, get_smr_note_sort_field
from main.xontology import XOntology, connect_concepts
from owlready2 import ThingClass, ObjectPropertyClass


class XmindImporter(NoteImporter):
    """
    Importer for Xmind files. You can add this class to anki.importing.Importers list to add it to ankis importers.
    """
    log: List[str]
    needMapper = False

    def __init__(self, col, file):
        NoteImporter.__init__(self, col, file)
        self._mw: AnkiQt = aqt.mw
        self._x_managers: List[XManager] = [XManager(os.path.normpath(file))]
        self._smr_world: SmrWorld = self._mw.smr_world
        self._translator: FieldTranslator = FieldTranslator()
        self._running: bool = True
        self._active_manager: Optional[XManager] = None
        self._current_sheet_import: str = ''
        self._notes_2_import: List[ForeignNote] = []
        # deck id, deck name, and repair are speciefied in deck selection dialog
        self._deck_id: Optional[int] = None
        self._deck_name: str = ''
        self._repair: bool = False
        # ontology is assigned when deck_id was selected
        self._onto: Optional[XOntology] = None
        self._register_referenced_x_managers(self._x_managers[0])
        # fields from Noteimporter:
        self.model: NoteType = col.models.byName(X_MODEL_NAME)
        self.allowHTML: bool = True
        # Fields to make methods from super class work
        self.needMapper: bool = True
        self.mapping: List[str] = list(SMR_NOTE_FIELD_NAMES.values())
        self.updateCount: int = 0
        self.importMode: int = ADD_MODE

    def newData(self, n: ForeignNote) -> List:
        """
        overrides NoteImporter's method newData() to additionally call smr_world.add_smr_note()
        :param n: the note whose data is to be processed and which is to be added to the smr world
        :return: the data needed to create a new anki note in a list
        """
        edge_id = n.tags.pop(-1)
        data = NoteImporter.newData(self, n)
        self._smr_world.add_smr_note(note_id=data[0], edge_id=edge_id, last_modified=data[3])
        return data

    def updateCards(self) -> None:
        """
        overrides NoteImporter's method updateCards() to avoid that cards' type and queue attributes are set to 2
        """
        return

    def open(self) -> None:
        """
        Starts deck selection dialog and runs import sheets with selected sheets
        """
        # check whether the file has already been imported before
        if self._smr_world.graph.execute("select * from xmind_files where path = '{seed_path}'".format(
                seed_path=self.file)).fetchone():
            self.log = ["It seems like {seed_path} is already in your collection. Please choose a different "
                        "file.".format(seed_path=self.file)]

    def _register_referenced_x_managers(self, x_manager: XManager):
        """
        Adds XManagers referenced by ref sheet to xManagers list
        :param x_manager: the XManager to get References from
        """
        ref_managers: List[XManager] = [XManager(f) for f in x_manager.get_referenced_files()]
        self._x_managers.extend(ref_managers)
        for manager in ref_managers:
            self._register_referenced_x_managers(manager)

    def initialize_import(self, user_inputs: DeckSelectionDialogUserInputsDTO) -> None:
        """
        Sets up the required fields for the import and initializes the import
        :param user_inputs: user inputs from the deck selection dialog
        """
        self._deck_id = user_inputs.deck_id
        self._deck_name = self.col.decks.get(self._deck_id)['name']
        self._repair = user_inputs.repair
        self._onto = XOntology(deck_id=self._deck_id, smr_world=self._smr_world)
        # Set model to Stepwise map retrieval model
        self.col.decks.select(self._deck_id)
        self.col.decks.current()['mid'] = self.model['id']
        self._mw.progress.start(immediate=True, label='importing...')
        self._mw.app.processEvents()
        self._mw.checkpoint("Import")
        for manager in self._x_managers:
            self.import_file(manager)
        self.finish_import()

    def import_file(self, x_manager: XManager):
        """
        Imports a file managed by the provided XManager and starts imports for all sheets in that file that contain
        concept maps
        :param x_manager: the x_manager that manages the file
        """
        self._active_manager = x_manager
        self._smr_world.add_xmind_file(x_manager=x_manager, deck_id=self._deck_id)
        for sheet in x_manager.get_content_sheets():
            self.import_sheet(sheet)

    def import_sheet(self, sheet: str):
        """
        imports the specified sheet and starts importing the map contained in that sheet starting from the root concept
        :param sheet: name of the sheet to be imported
        :return: adds the roottopic of the active sheet to self.onto and starts
                the map import by calling getQuestions
        """
        self._current_sheet_import = sheet
        self._mw.progress.update(label='importing %s' % sheet, maybeShow=False)
        self._mw.app.processEvents()
        self._smr_world.add_xmind_sheet(x_manager=self._active_manager, sheet_name=sheet)
        root_node = self._active_manager.get_root_node(sheet=sheet)
        self.import_node_if_concept(node=root_node,
                                    concepts=[self._onto.concept_from_node_content(get_node_content(root_node))])

    def import_node_if_concept(
            self, node: bs4.Tag, concepts: List[ThingClass], parent_node_ids: Optional[List[str]] = None,
            parent_concepts: Optional[List[ThingClass]] = None, parent_edge_id: Optional[str] = None,
            parent_relationship_class_name: Optional[str] = None, order_number: int = 1) -> None:
        """
        If the node is not empty:
        - adds a node to the smr world
        - adds image and media files from the node to the anki collection
        - calls import_triple() for each parent node preceding the parent edge
        Finally calls import_edge() for each edge following the node.
        :param node: the tag representing the node to import
        :param concepts: A list of concepts that only contains one concept if the node that is imported is not
        empty. Multiple concepts if the node is empty to serve as a representation of multiple concepts preceding a
        relation. In this case the list serves
        :param parent_node_ids: list of xmind ids of parent nodes for the triples that are imported for this node
        :param parent_concepts: list of concepts of parent nodes for creating the ontology relationships preceding
        this node
        :param parent_edge_id: xmind id of the node's parent edge
        :param parent_relationship_class_name: class name for the relationship in the triple that we import into the
        ontology
        :param order_number: order number of the node with respect to its siblings
        """
        if parent_node_ids is None:
            parent_node_ids = []
        if parent_concepts is None:
            parent_concepts = []
        if not is_empty_node(node):
            node_content = get_node_content(node)
            # add image and media to the anki collection
            self._smr_world.add_image_and_media_to_collection_and_self(
                content=node_content, collection=self.col, x_manager=self._active_manager)
            # add the node to the smr world
            self._smr_world.add_xmind_node(
                node=node, node_content=node_content, ontology_storid=concepts[0].storid,
                sheet_id=self._active_manager.get_sheet_id(self._current_sheet_import), order_number=order_number)
            # import a triple for each parent concept
            for parent_node_id, parent_concept in zip(parent_node_ids, parent_concepts):
                self.import_triple(parent_node_id=parent_node_id, parent_thing=parent_concept, edge_id=parent_edge_id,
                                   child_node_id=node['id'], child_thing=concepts[0],
                                   relationship_class_name=parent_relationship_class_name)
            node_ids_preceding_next_edge: List[str] = [node['id']]
        else:
            node_ids_preceding_next_edge: List[str] = [n['id'] for n in get_non_empty_sibling_nodes(node)]
        # import each child edge
        for order_number, following_relationship in enumerate(get_child_nodes(node), start=1):
            if following_relationship.text == 'pronounciation':
                assert True
            self.import_edge(order_number=order_number, edge=following_relationship,
                             parent_node_ids=node_ids_preceding_next_edge, parent_concepts=concepts)

    def import_triple(self, parent_node_id: str, parent_thing: ThingClass, edge_id: str, relationship_class_name: str,
                      child_node_id: str, child_thing: ThingClass, ) -> None:
        """
        connects the specified concepts in the ontology using the specified relationship class name and adds the
        triple of parent node, edge, and concept to the smr world
        :param parent_node_id: xmind id of the parent node
        :param parent_thing: ontology concept representing the parent node
        :param edge_id: xmind id of the edge
        :param relationship_class_name: ontology class name of the relationship
        :param child_node_id: xmind id of the child node
        :param child_thing: ontology concept representing the child node
        """
        connect_concepts(child_thing=child_thing, relationship_class_name=relationship_class_name,
                         parent_thing=parent_thing)
        self._smr_world.add_smr_triple(parent_node_id=parent_node_id, edge_id=edge_id, child_node_id=child_node_id,
                                       card_id=None)

    def import_edge(self, order_number: int, edge: bs4.Tag, parent_node_ids: List[str],
                    parent_concepts: List[ThingClass]) -> None:
        """
        - creates concepts for all non-empty all the edge represented by the specified tag
        - adds the relationship property to the ontology
        - adds the edge to the smr world
        - adds image and media from the edge to the anki collection
        - calls import_node_if_concept() for each child node following the edge.
        :param order_number: order number of the edge with respect to its siblings
        :param edge: tag that represents the edge to be imported
        :param parent_node_ids: list of xmind ids of parent nodes
        :param parent_concepts: list of concepts of parent nodes
        """
        edge_content: NodeContentDTO = get_node_content(edge)
        child_nodes: List[bs4.Tag] = get_child_nodes(edge)
        # stop execution and warn if an edge is not followed by any nodes
        if len(child_nodes) == 0:
            self._running = False
            self.log = [
                "Warning:\nA Question titled {title} (path {path}) is missing answers. Please adjust your Concept Map "
                "and try again.".format(
                    title=edge_content.title, path=get_edge_coordinates_from_parent_node(
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
            self._running = False
            self.log = [
                "Warning:\nA Question titled \"{title}\" has more than {n_answers} answers. Make sure every Question "
                "in your Map is followed by no more than {n_answers} Answers and try again.".format(
                    title=get_node_title(edge), n_answers=X_MAX_ANSWERS)]
            return
        # create the concepts for the next iteration beforehand to be able to assign a list of all sibling concepts
        # to empty nodes for creating relationships following multiple concepts
        node_contents = [get_node_content(n) for n in non_empty_child_nodes]
        all_child_concepts = [self._onto.concept_from_node_content(node_content=n, node_is_root=False) for n in
                              node_contents]
        single_child_concepts = [[concept] for concept in all_child_concepts]
        # add the relation to the ontology
        relationship_class_name: str = self._translator.class_from_content(edge_content)
        if not relationship_class_name:
            relationship_class_name = self._onto.CHILD_CLASS_NAME
        relationship_property: ObjectPropertyClass = self._onto.add_relation(relationship_class_name)
        # add node image and media to anki if edge is not empty
        if relationship_class_name != self._onto.CHILD_CLASS_NAME:
            self._smr_world.add_image_and_media_to_collection_and_self(
                content=edge_content, collection=self.col, x_manager=self._active_manager)
        # add the edge to the smr world
        self._smr_world.add_xmind_edge(
            edge=edge, edge_content=edge_content,
            sheet_id=self._active_manager.get_sheet_id(self._current_sheet_import),
            order_number=order_number, ontology_storid=relationship_property.storid)
        # import each child_node either with a list of the single concept or a list of all concepts if they are empty
        for order_number, (child_node, child_concepts) in enumerate(zip(
                non_empty_child_nodes + empty_child_nodes,
                single_child_concepts + len(empty_child_nodes) * [all_child_concepts]), start=1):
            self.import_node_if_concept(
                node=child_node, concepts=child_concepts, parent_node_ids=parent_node_ids,
                parent_concepts=parent_concepts, parent_edge_id=edge['id'],
                parent_relationship_class_name=relationship_class_name, order_number=order_number)
        if edge_content.title == 'pronounciation':
            assert True
        # create the note and add it to anki's collection if the edge is not empty
        if relationship_class_name != self._onto.CHILD_CLASS_NAME:
            self.create_and_add_note(edge['id'])

    def get_x_managers(self) -> List[XManager]:
        return self._x_managers

    def create_and_add_note(self, edge_id: str) -> None:
        """
        Creates a Note to add to the collection and adds it to the list of notes to be imported
        :param edge_id: Xmind id of the edge belonging to the note to be imported
        """
        note = ForeignNote()
        reference_field = [get_smr_note_reference_field(smr_world=self._smr_world, edge_id=edge_id)]
        question_field = [self._smr_world.get_smr_note_question_field(edge_id)]
        answer_fields = self._smr_world.get_smr_note_answer_fields(edge_id)
        sort_field = [get_smr_note_sort_field(smr_world=self._smr_world, edge_id=edge_id)]
        note.fields = reference_field + question_field + answer_fields + (X_MAX_ANSWERS - len(answer_fields)) * [
            ''] + sort_field
        note.tags.append(self._active_manager.acquire_anki_tag(
            deck_name=self._deck_name, sheet_name=self._current_sheet_import))
        # add the edge id to the tags list to be able to assign the note to the right edge during import
        note.tags.append(edge_id)
        # note.deck = self.deck_id
        note.cards = {i: ForeignCard() for i, _ in enumerate(answer_fields, start=1)}
        note.fieldsStr = joinFields(note.fields)
        self._notes_2_import.append(note)

    def finish_import(self):
        """
        - Cancels the import if something went wrong
        - Adds Notes to the anki collection
        - Registers the notes in the smr world
        - Adds card ids from imported notes to the triples they belong to in the smr world
        - Saves the smr world
        """
        if not self._running:
            return
        # Add all notes to the collection
        self.importNotes(self._notes_2_import)
        # remove log entries informing about duplicate fields
        self.log = [self.log[-1]]
        for card in self._cards:
            card_id = self.col.db.first("select id from cards where nid = ? and ord = ?", card[0], card[1] - 1)[0]
            self._smr_world.update_smr_triples_card_id(note_id=card[0], order_number=card[1], card_id=card_id)
            # manually set the deck until I find a better solution, 
            # see https://forums.ankiweb.net/t/importnotes-always-adds-cards-to-default-deck/1690 for issue
            self.col.db.executemany("update cards set did = ? where id = ?", [(self._deck_id, card_id)])
        self._smr_world.save()
        self._mw.reset(guiOnly=True)
        self._mw.progress.finish()

# old code
# def partial_import(self, seed_topic, sheet_id, deck_id, parent_q,
#                    parent_as, onto=None):
#     """
#     Imports questions starting at a given point
#     :param onto: Optional, Ontology to set as importer's ontology:
#     :param seed_topic: Tag of the topic of the question to start at
#     :param sheet_id: Xmind id of the sheet the question belongs to
#     :param deck_id: Deck-id of the deck to import to
#     :param parent_q: Tag of the parent-question of the question the
#     import starts at
#     :param parent_as: List of tags of the answers to the parent-question
#     """
#     self.set_up_import(deck_id=deck_id, sheet=sheet_id, onto=onto)
#     self.col.decks.select(self.deck_id)
#     self.col.decks.current()['mid'] = self.col.models.byName(
#         X_MODEL_NAME)['id']
#     parent_a_concepts = [self.onto.get_answer_by_a_id(
#         a_id=a['id'], q_id=parent_q['id']) for a in parent_as]
#     if len(parent_as) > 1:
#         node_tag = None
#         a_concept = parent_a_concepts
#     else:
#         node_tag = parent_as[0]
#         a_concept = parent_a_concepts[0]
#     parent_a_dict = self.get_answer_dict(
#         node_tag=node_tag, question=parent_q['id'], root=False,
#         a_concept=a_concept)
#
#     # If the seed_topic's parent follows a bridge, start importing at the
#     # bridge instead
#     parent_q_children = get_child_nodes(parent_q)
#     if get_parent_node(seed_topic) not in parent_q_children:
#         if len(parent_as) > 1:
#             seed_topic = next(
#                 g for c in parent_q_children if is_empty_node(c) for
#                 g in get_child_nodes(c) if seed_topic.text in g.text)
#         else:
#             seed_topic = next(t for t in get_child_nodes(parent_as[0]) if
#                               seed_topic.text in t.text)
#     ref, sort_id = self.active_manager.ref_and_sort_id(q_topic=seed_topic)
#     q_index = sum(1 for _ in seed_topic.previous_siblings) + 1
#     self.import_edge(order_number=q_index, edge=seed_topic)
#
# def set_up_import(self, deck_id, sheet, onto=None):
#     self.current_sheet_import = next(
#         s for m in self.x_managers for
#         s in m._sheets if m._sheets[s]['tag']['id'] == sheet)
#     self.active_manager = next(
#         m for m in self.x_managers for
#         s in m._sheets if s == self.current_sheet_import)
#     self.deck_id = deck_id
#     if onto:
#         self.onto = onto
#     else:
#         self.onto = XOntology(deck_id)
#     self.deck_name = self.col.decks.get(self.deck_id)['name']
#
# def maybe_sync(self, sheet_id, note_list):
#     if self.repair:
#         # noinspection PyTypeChecker
#         existing_notes = list(self.col.db.execute(
#             "select id, flds from notes where tags like '%" +
#             self.current_sheet_import['tag'].replace(" ", "") + "%'"))
#     else:
#         existing_notes = getNotesFromSheet(sheetId=sheet_id, col=self.col)
#     if existing_notes:
#         notes_2_add = []
#         notes_2_update = []
#         old_q_id_list = list(map(lambda n: json.loads(
#             splitFields(n[1])[list(SMR_NOTE_FIELD_NAMES.keys()).index('mt')])[
#             'questionId'], existing_notes))
#         for newNote in note_list:
#             new_fields = splitFields(newNote[6])
#             new_meta = json.loads(new_fields[list(SMR_NOTE_FIELD_NAMES.keys()).index('mt')])
#             new_q_id = new_meta['questionId']
#             try:
#                 if self.repair:
#                     new_qt_x_aw = joinFields(new_fields[1:22])
#                     old_tpl = tuple(
#                         filter(lambda n: new_qt_x_aw in n[1], existing_notes))[0]
#                     note_id = existing_notes.index(old_tpl)
#                 else:
#                     note_id = old_q_id_list.index(new_q_id)
#                     # if the fields are different, add it to notes to be updated
#                 if not existing_notes[note_id][1] == newNote[6]:
#                     notes_2_update.append(
#                         [existing_notes[note_id], newNote])
#                 del existing_notes[note_id]
#                 del old_q_id_list[note_id]
#             except (ValueError, IndexError):
#                 notes_2_add.append(newNote)
#         self.addNew(notes_2_add)
#         self.log[0][1] += len(notes_2_add)
#         self.addUpdates(notes_2_update)
#         self.log[1][1] += len(notes_2_update)
#         self.removeOld(existing_notes)
#         self.log[2][1] += len(existing_notes)
#         self.col.save()
#     else:
#         notes_2_add = note_list
#         self.addNew(notes_2_add)
#         self.log[0][1] += len(notes_2_add)
#
# def removeOld(self, existingNotes):
#     oldIds = list(map(lambda nt: nt[0], existingNotes))
#     self.col.remNotes(oldIds)
#
# def getCardUpdates(self, aIds, noteTpl):
#     cardUpdates = []
#     # Get relevant values of the prior answers
#     relevantVals = ['type', 'queue', 'due', 'ivl', 'factor', 'reps',
#                     'lapses', 'left', 'odue', 'flags']
#     # remember prior values of cards that have moved
#     oldVals = list(self.col.db.execute(
#         "select " + ", ".join(relevantVals) + " from cards where nid = " +
#         str(noteTpl[0][0])))
#     for i, aId in enumerate(aIds[1], start=0):
#         # if this answer was a different answer before, remember the
#         # stats
#         try:
#             if aId != aIds[0][i]:
#                 try:
#                     cardUpdates.append(oldVals[aIds[0].index(aId)])
#                 except ValueError:
#                     # if this answer was not in the old answers at all
#                     # get Values for a completely new card
#                     cardUpdates.append([str(0)] * 10)
#             else:
#                 # if this answer was the same answer before, ignore it
#                 cardUpdates.append('')
#         except IndexError:
#             # if this answer was not in the old answers at all
#             # get Values for a completely new card
#             cardUpdates.append([str(0)] * 10)
#     return cardUpdates
#
# def update_status(self):
#     for manager in self.x_managers:
#         remote = manager.get_remote()
#         local = self.note_manager.get_local(manager._file)
#         status = deep_merge(remote=remote, local=local)
#         self.status_manager.add_new(status)
#     self.status_manager.save()
#
# def import_ontology(self):
#     triples = [self.onto.getElements(t) for t in self.onto.getNoteTriples() if
#                t[1] in self.added_relations['storids']]
#     triples_with_q_ids = [self.onto.q_id_elements(t) for t in triples]
#     added_triples = [t for t in triples_with_q_ids if t['q_id'] in self.added_relations['q_ids']]
#     question_list = get_question_sets(added_triples)
#     notes = [self.note_from_question_list(q) for q in question_list]
#     self.addNew(notes=notes)
#     self.add_image_and_media()
