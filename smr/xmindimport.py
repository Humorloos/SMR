import os
from typing import List, Optional, Dict, Collection

import bs4

import aqt as aqt
from anki.importing.noteimp import NoteImporter, ForeignNote, ADD_MODE
from anki.models import NoteType
from aqt.main import AnkiQt
from owlready2 import ThingClass, ObjectPropertyClass
from smr.consts import X_MODEL_NAME, X_MAX_ANSWERS, SMR_NOTE_FIELD_NAMES
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindnodedto import XmindNodeDto
from smr.dto.xmindsheetdto import XmindSheetDto
from smr.fieldtranslator import FieldTranslator
from smr.smrworld import SmrWorld
from smr.utils import get_edge_coordinates_from_parent_node
from smr.xmanager import is_empty_node, XManager, get_non_empty_sibling_nodes, \
    get_topic_content
from smr.xmindsheet import get_child_nodes
from smr.xontology import XOntology


class XmindImporter(NoteImporter):
    """
    Importer for Xmind files. You can add this class to anki.importing.Importers list to add it to ankis importers.
    """
    log: List[str]
    needMapper = False

    def __init__(self, col: Collection, file: str):
        NoteImporter.__init__(self, col, file)
        self.mw: AnkiQt = aqt.mw
        self.x_manager: List[XManager] = []
        self.smr_world: SmrWorld = self.mw.smr_world
        self._translator: FieldTranslator = FieldTranslator()
        self.is_running: bool = True
        self.current_sheet_import: str = ''
        self.edge_ids_2_make_notes_of: List[str] = []
        self.notes_2_import: Dict[str, ForeignNote] = {}
        # entity lists for imports
        self.files_2_import: List[XmindFileDto] = []
        self.sheets_2_import: List[XmindSheetDto] = []
        self.media_2_anki_files_2_import: List[XmindMediaToAnkiFilesDto] = []
        self.nodes_2_import: List[XmindNodeDto] = []
        self.edges_2_import: List[XmindNodeDto] = []
        self.triples_2_import: List[SmrTripleDto] = []
        self.smr_notes_2_add: List[SmrNoteDto] = []
        # deck id, deck name, and repair are speciefied in deck selection dialog
        self.deck_id: Optional[int] = None
        self.deck_name: str = ''
        self.repair: bool = False
        # ontology is assigned when deck_id was selected
        self.onto: Optional[XOntology] = None
        # fields from Noteimporter:
        self.model: NoteType = col.models.byName(X_MODEL_NAME)
        self.allowHTML: bool = True
        # Fields to make methods from super class work
        self.needMapper: bool = True
        self.mapping: List[str] = list(SMR_NOTE_FIELD_NAMES.values())
        self.updateCount: int = 0
        self.importMode: int = ADD_MODE

    @property
    def deck_name(self):
        if not self._deck_name:
            self.deck_name = self.col.decks.get(self.deck_id)['name']
        return self._deck_name

    @deck_name.setter
    def deck_name(self, value):
        self._deck_name = value

    @property
    def edge_ids_2_make_notes_of(self) -> List[str]:
        return self._edges_2_make_notes_of

    @edge_ids_2_make_notes_of.setter
    def edge_ids_2_make_notes_of(self, value: List[str]):
        self._edges_2_make_notes_of = value

    @property
    def current_sheet_import(self):
        return self._current_sheet_import

    @current_sheet_import.setter
    def current_sheet_import(self, value):
        self._current_sheet_import = value

    @property
    def deck_id(self) -> Optional[int]:
        return self._deck_id

    @property
    def files_2_import(self) -> List[XmindFileDto]:
        return self._files_2_import

    @property
    def sheets_2_import(self) -> List[XmindSheetDto]:
        return self._sheets_2_import

    @property
    def media_2_anki_files_2_import(self) -> List[XmindMediaToAnkiFilesDto]:
        return self._media_2_anki_files_2_import

    @property
    def nodes_2_import(self) -> List[XmindNodeDto]:
        return self._nodes_2_import

    @property
    def edges_2_import(self) -> List[XmindNodeDto]:
        return self._edges_2_import

    @property
    def triples_2_import(self) -> List[SmrTripleDto]:
        return self._triples_2_import

    @property
    def mw(self) -> AnkiQt:
        return self._mw

    @mw.setter
    def mw(self, value):
        self._mw = value

    @property
    def notes_2_import(self) -> Dict[str, ForeignNote]:
        return self._notes_2_import

    @notes_2_import.setter
    def notes_2_import(self, value: Dict[str, ForeignNote]):
        self._notes_2_import = value

    @property
    def x_manager(self) -> XManager:
        if not self._x_manager:
            self.x_manager = XManager(os.path.normpath(self.file))
        return self._x_manager

    @x_manager.setter
    def x_manager(self, value: XManager):
        self._x_manager = value

    @property
    def repair(self):
        return self._repair

    @repair.setter
    def repair(self, value):
        self._repair = value

    @property
    def is_running(self) -> bool:
        return self._is_running

    @is_running.setter
    def is_running(self, value: bool):
        self._is_running = value

    @property
    def smr_world(self) -> SmrWorld:
        return self._smr_world

    @smr_world.setter
    def smr_world(self, value: SmrWorld):
        self._smr_world = value

    @deck_id.setter
    def deck_id(self, value):
        self._deck_id = value

    @property
    def onto(self) -> XOntology:
        return self._onto

    @onto.setter
    def onto(self, value: XOntology):
        self._onto = value

    @property
    def smr_notes_2_add(self) -> List[SmrNoteDto]:
        return self._smr_notes_2_add

    @media_2_anki_files_2_import.setter
    def media_2_anki_files_2_import(self, value):
        self._media_2_anki_files_2_import = value

    @sheets_2_import.setter
    def sheets_2_import(self, value):
        self._sheets_2_import = value

    @files_2_import.setter
    def files_2_import(self, value):
        self._files_2_import = value

    @nodes_2_import.setter
    def nodes_2_import(self, value):
        self._nodes_2_import = value

    @edges_2_import.setter
    def edges_2_import(self, value):
        self._edges_2_import = value

    @triples_2_import.setter
    def triples_2_import(self, value):
        self._triples_2_import = value

    @smr_notes_2_add.setter
    def smr_notes_2_add(self, value):
        self._smr_notes_2_add = value

    def newData(self, n: ForeignNote) -> List:
        """
        overrides NoteImporter's method newData() to additionally call smr_world.add_or_replace_smr_notes()
        :param n: the note whose data is to be processed and which is to be added to the smr world
        :return: the data needed to create a new anki note in a list
        """
        edge_id = n.tags.pop(-1)
        data = NoteImporter.newData(self, n)
        self.smr_notes_2_add.append(SmrNoteDto(note_id=data[0], edge_id=edge_id, last_modified=data[3]))
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
        directory, file_name = os.path.split(self.file)
        file_name = os.path.splitext(file_name)[0]
        if self.smr_world.graph.execute(f"select * from xmind_files where directory = '{directory}' and "
                                        f"file_name = '{file_name}'").fetchone():
            self.log = [f"It seems like {self.file} is already in your collection. Please choose a different "
                        "file."]
            self.is_running = False

    def initialize_import(self, user_inputs: DeckSelectionDialogUserInputsDTO) -> None:
        """
        Sets up the required fields for the import and initializes the import
        :param user_inputs: user inputs from the deck selection dialog
        """
        self.deck_id = user_inputs.deck_id
        self.repair = user_inputs.repair
        self.onto = XOntology(deck_id=self.deck_id, smr_world=self.smr_world)
        # Set model to Stepwise map retrieval model
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        self._import_file()
        self._add_entities_2_smr_world()
        # Create Notes from all edges
        self.notes_2_import = self.smr_world.generate_notes(self.col, edge_ids=self.edge_ids_2_make_notes_of)

    def import_sheet(self, sheet_id: str):
        """
        Imports only the sheet with the specified id and adds its contents to the smr world
        :param sheet_id:
        :return:
        """
        self._import_sheet(sheet_id)
        self._add_entities_2_smr_world()
        self.notes_2_import = self.smr_world.generate_notes(self.col, edge_ids=self.edge_ids_2_make_notes_of)

    def _import_file(self):
        """
        Imports a file managed by the provided XManager and starts imports for all sheets in that file that contain
        concept maps
        """
        directory, file_name = self.x_manager.get_directory_and_file_name()
        self.files_2_import.append(XmindFileDto(
            directory=directory, file_name=file_name,
            map_last_modified=self.x_manager.map_last_modified, file_last_modified=self.x_manager.file_last_modified,
            deck_id=self.deck_id))
        for sheet in self.x_manager.sheets:
            self._import_sheet(sheet)

    def _import_sheet(self, sheet_id: str) -> None:
        """
        Imports the specified sheet and starts importing the map contained in that sheet starting from the root concept
        :param sheet_id: name of the sheet to be imported
        """
        self.current_sheet_import = sheet_id
        sheet_name = self.x_manager.sheets[sheet_id].name
        self.mw.progress.update(label='importing %s' % sheet_name, maybeShow=False)
        self.mw.app.processEvents()
        directory, file_name = self.x_manager.get_directory_and_file_name()
        self.sheets_2_import.append(XmindSheetDto(
            sheet_id=sheet_id, name=sheet_name, file_directory=directory, file_name=file_name,
            last_modified=self.x_manager.sheets[sheet_id].last_modified))
        root_node = self.x_manager.sheets[sheet_id].root_node
        root_concept = self.onto.concept_from_node_content(
            self.x_manager.get_topic_content(root_node), node_id=root_node['id'], node_is_root=True)
        self.import_node_if_concept(node=root_node, concepts=[root_concept])

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
            node_content = self.x_manager.get_topic_content(node)
            # add image and media to the anki collection
            self.add_image_and_media_to_collection(node_content)
            # add the node to the smr world
            self.nodes_2_import.append(XmindNodeDto(
                node_id=node['id'], sheet_id=self.current_sheet_import,
                title=node_content.title, image=node_content.image, link=node_content.media,
                ontology_storid=concepts[0].storid, last_modified=node['timestamp'], order_number=order_number))
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

    def add_image_and_media_to_collection(self, content: TopicContentDto) -> None:
        """
        - If present, adds media and image specified in the content DTO to the anki collection and media folder
        - Records an entry linking the potentially new file name to the media attachment / hyperlink from the xmind map
        to media_to_anki_files_2_import list
        :param content: the content of the xmind node to add the image and media for
        """
        if content.media:
            # xmind 8 adds prefix attachments, xmind zen adds prefix resources
            if content.media.startswith(('attachments', 'resources')):
                new_media_name = self.col.media.write_data(desired_fname=content.media,
                                                           data=self.x_manager.read_attachment(content.media))
            # if media file was not attached but only referenced via hyperlink
            else:
                new_media_name = self.col.media.add_file(content.media)
            self.media_2_anki_files_2_import.append(XmindMediaToAnkiFilesDto(
                xmind_uri=content.media, anki_file_name=new_media_name))
        if content.image:
            new_image_name = self.col.media.write_data(desired_fname=content.image,
                                                       data=self.x_manager.read_attachment(content.image))
            self.media_2_anki_files_2_import.append(XmindMediaToAnkiFilesDto(
                xmind_uri=content.image, anki_file_name=new_image_name))

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
        self.onto.connect_concepts(child_thing=child_thing, relationship_class_name=relationship_class_name,
                                   parent_thing=parent_thing, edge_id=edge_id)
        self.triples_2_import.append(SmrTripleDto(
            parent_node_id=parent_node_id, edge_id=edge_id, child_node_id=child_node_id))

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
        edge_content: TopicContentDto = self.x_manager.get_topic_content(edge)
        child_nodes: List[bs4.Tag] = get_child_nodes(edge)
        # stop execution and warn if an edge is not followed by any nodes
        if len(child_nodes) == 0:
            self.is_running = False
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
        if not edge_content.is_empty() and len(non_empty_child_nodes) > X_MAX_ANSWERS:
            self.is_running = False
            self.log = [
                "Warning:\nA Question titled \"{title}\" has more than {n_answers} answers. Make sure every Question "
                "in your Map is followed by no more than {n_answers} Answers and try again.".format(
                    title=get_topic_content(edge), n_answers=X_MAX_ANSWERS)]
            return
        # create the concepts for the next iteration beforehand to be able to assign a list of all sibling concepts
        # to empty nodes for creating relationships following multiple concepts
        all_child_concepts = [self.onto.concept_from_node_content(node_content=self.x_manager.get_topic_content(
            n), node_id=n['id'], node_is_root=False) for n in non_empty_child_nodes]
        single_child_concepts = [[concept] for concept in all_child_concepts]
        # add the relation to the ontology
        relationship_class_name = self.smr_world.child_relation_name if edge_content.is_empty() \
            else self._translator.relation_class_from_content(edge_content)
        relationship_property: ObjectPropertyClass = self.onto.add_relation(relationship_class_name)
        # add node image and media to anki if edge is not empty
        if relationship_class_name != self.smr_world.child_relation_name:
            self.add_image_and_media_to_collection(edge_content)
        # add the edge to the smr world
        self.edges_2_import.append(XmindNodeDto(
            node_id=edge['id'], sheet_id=self.current_sheet_import, title=edge_content.title, image=edge_content.image,
            link=edge_content.media, ontology_storid=relationship_property.storid, last_modified=edge['timestamp'],
            order_number=order_number))
        # if the edge is not empty, add it to the list of edges to make notes from
        if not edge_content.is_empty():
            self.edge_ids_2_make_notes_of.append(edge['id'])
        # import each child_node either with a list of the single concept or a list of all concepts if they are empty
        for order_number, (child_node, child_concepts) in enumerate(zip(
                non_empty_child_nodes + empty_child_nodes,
                single_child_concepts + len(empty_child_nodes) * [all_child_concepts]), start=1):
            self.import_node_if_concept(
                node=child_node, concepts=child_concepts, parent_node_ids=parent_node_ids,
                parent_concepts=parent_concepts, parent_edge_id=edge['id'],
                parent_relationship_class_name=relationship_class_name, order_number=order_number)

    def finish_import(self) -> None:
        """
        - Cancels the import if something went wrong
        - Imports notes and cards from list notes_2_import
        - Saves the smr world
        """
        if not self.is_running:
            return
        self.import_notes_and_cards()
        self.smr_world.save()
        self.mw.reset(guiOnly=True)
        self.mw.progress.finish()

    def import_notes_and_cards(self) -> None:
        """
        - Adds Notes to the anki collection
        - Registers the notes in the smr world
        - Adds card ids from imported notes to the triples they belong to in the smr world
        """
        # Add all notes to the collection
        self.col.decks.select(self.deck_id)
        deck = self.col.decks.get(self.deck_id)
        deck['mid'] = self.model['id']
        self.col.decks.save(deck)
        self.model['did'] = self.deck_id
        self.col.models.save(self.model)
        self.importNotes(list(self.notes_2_import.values()))
        # Link imported notes to edges
        self.smr_world.add_or_replace_smr_notes(self.smr_notes_2_add)
        # remove log entries informing about duplicate fields
        self.log = [self.log[-1]]
        # Add card ids to smr triples relation in smr world
        self.smr_world.update_smr_triples_card_ids(data=[(card[0], card[1]) for card in self._cards],
                                                   collection=self.col)

    def _add_entities_2_smr_world(self) -> None:
        """
        Adds all entities in the respectives lists to the respective relations (except notes and cards since they
        need to be imported to the anki collection first)
        """
        # Add all files to the smr world
        self.smr_world.add_or_replace_xmind_files(self.files_2_import)
        # Add all sheets to the smr world
        self.smr_world.add_xmind_sheets(self.sheets_2_import)
        # Add all media and images to the smr world
        self.smr_world.add_xmind_media_to_anki_files(self._media_2_anki_files_2_import)
        # Add all nodes to the smr world
        self.smr_world.add_or_replace_xmind_nodes(self.nodes_2_import)
        # Add all edges to the smr world
        self.smr_world.add_or_replace_xmind_edges(self.edges_2_import)
        # Add all triples to the smr world
        self.smr_world.add_smr_triples(self.triples_2_import)

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
#         s for m in self.x_manager for
#         s in m._sheets if m._sheets[s]['tag']['id'] == sheet)
#     self.active_manager = next(
#         m for m in self.x_manager for
#         s in m._sheets if s == self.current_sheet_import)
#     self.deck_id = deck_id
#     if onto:
#         self.onto = onto
#     else:
#         self.onto = XOntology(deck_id)
#     self.deck_name = self.col.decks.get(self.deck_id)['name']
