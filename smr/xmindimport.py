import os
from typing import List, Optional, Dict, Union, Set

import aqt as aqt
from anki import Collection
from anki.importing.noteimp import NoteImporter, ForeignNote, ADD_MODE
from anki.models import NoteType
from aqt.main import AnkiQt
from smr.cachedproperty import cached_property
from smr.consts import X_MODEL_NAME, SMR_NOTE_FIELD_NAMES
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.dto.smrnotedto import SmrNoteDto
from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindmediatoankifilesdto import XmindMediaToAnkiFilesDto
from smr.dto.xmindsheetdto import XmindSheetDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.smrworld import SmrWorld
from smr.xmanager import XManager
from smr.xmindsheet import MapError
from smr.xmindtopic import XmindNode, XmindEdge
from smr.xontology import XOntology


class XmindImporter(NoteImporter):
    """
    Importer for Xmind files. You can add this class to anki.importing.Importers list to add it to anki's importers.
    """
    log: List[str]
    needMapper = False

    def __init__(self, col: Collection, file: str, onto: Optional[XOntology] = None):
        NoteImporter.__init__(self, col, file)
        self.mw: AnkiQt = aqt.mw
        self.smr_world: SmrWorld = self.mw.smr_world
        # if no ontology is provided, it is assigned later
        self.onto = onto
        self.is_running: bool = True
        self.notes_2_import = {}
        self.media_uris_2_add = None
        # entity lists for imports
        self.files_2_import: List[XmindFileDto] = []
        self.sheets_2_import: List[XmindSheetDto] = []
        self.smr_notes_2_add: List[SmrNoteDto] = []
        # deck id, deck name, and repair are specified in deck selection dialog
        self.deck_name: str = ''
        self.repair: bool = False
        # fields from NoteImporter:
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
            self.deck_name = self.col.decks.get(self.onto.deck_id)['name']
        return self._deck_name

    @deck_name.setter
    def deck_name(self, value):
        self._deck_name = value

    @property
    def edge_ids_2_make_notes_of(self) -> Set[str]:
        try:
            return self._edge_ids_2_make_notes_of
        except AttributeError:
            self._edge_ids_2_make_notes_of = set()
            return self._edge_ids_2_make_notes_of

    @edge_ids_2_make_notes_of.setter
    def edge_ids_2_make_notes_of(self, value: Set[str]):
        self._edge_ids_2_make_notes_of = value

    @property
    def files_2_import(self) -> List[XmindFileDto]:
        return self._files_2_import

    @property
    def sheets_2_import(self) -> List[XmindSheetDto]:
        return self._sheets_2_import

    @cached_property
    def media_2_anki_files_2_import(self) -> List[XmindMediaToAnkiFilesDto]:
        return []

    @cached_property
    def edges_2_import(self) -> List[XmindTopicDto]:
        return []

    @cached_property
    def smr_triples_2_import(self) -> List[SmrTripleDto]:
        return []

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
        try:
            return self._x_manager
        except AttributeError:
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

    @property
    def smr_notes_2_add(self) -> List[SmrNoteDto]:
        return self._smr_notes_2_add

    @sheets_2_import.setter
    def sheets_2_import(self, value):
        self._sheets_2_import = value

    @files_2_import.setter
    def files_2_import(self, value):
        self._files_2_import = value

    @smr_notes_2_add.setter
    def smr_notes_2_add(self, value):
        self._smr_notes_2_add = value

    @property
    def media_uris_2_add(self) -> List[str]:
        if self._media_uris_2_add is None:
            self._media_uris_2_add = []
        return self._media_uris_2_add

    @media_uris_2_add.setter
    def media_uris_2_add(self, value: List[str]):
        self._media_uris_2_add = value

    @cached_property
    def nodes_4_concepts(self) -> List[XmindTopicDto]:
        return []

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
        checks whether the file has already been imported before
        """
        directory, file_name = os.path.split(self.file)
        file_name = os.path.splitext(file_name)[0]
        if self.smr_world.graph.execute(f"select * from xmind_files where directory = '{directory}' and "
                                        f"file_name = '{file_name}'").fetchone():
            self.log = [f"It seems like {self.file} is already in your collection. Please choose a different "
                        "file."]
            self.is_running = False

    def initialize_import(self, user_inputs: DeckSelectionDialogUserInputsDTO) -> None:
        """
        - Sets up the required fields for the import
        - Starts the import of the whole xmind file
        - Adds the collected data to the smr world
        - Generates the notes to be imported on finish import from the imported data
        :param user_inputs: user inputs from the deck selection dialog
        """
        self.repair = user_inputs.repair
        self.onto = XOntology(deck_id=user_inputs.deck_id, smr_world=self.smr_world)
        # Set model to Stepwise map retrieval model
        self.mw.progress.start(immediate=True, label='importing...')
        self.mw.app.processEvents()
        self.mw.checkpoint("Import")
        self._import_file()

    def add_media_2_anki_collection(self) -> None:
        """
        Adds all media that was registered in media_uris_2_add to the anki collection with the correct method for paths
        or attachments
        """
        for uri in self.media_uris_2_add:
            # if media file was not attached but only referenced via hyperlink, add it via add_file()
            if os.path.isfile(uri):
                new_media_name = self.col.media.add_file(uri)
            # otherwise, extract the file and add it via write_data()
            else:
                new_media_name = self.col.media.write_data(desired_fname=uri,
                                                           data=self.x_manager.read_attachment(uri))
            self.media_2_anki_files_2_import.append(XmindMediaToAnkiFilesDto(
                xmind_uri=uri, anki_file_name=new_media_name))

    def import_sheet(self, sheet_id: str):
        """
        Imports only the sheet with the specified id and adds its contents to the smr world
        :param sheet_id: xmind id of the sheet to import
        """
        self._import_sheet(sheet_id)

    def _import_file(self):
        """
        Imports a file managed by the provided XManager and starts imports for all sheets in that file that contain
        concept maps
        """
        directory, file_name = self.x_manager.get_directory_and_file_name()
        self.files_2_import.append(XmindFileDto(
            directory=directory, file_name=file_name,
            map_last_modified=self.x_manager.map_last_modified, file_last_modified=self.x_manager.file_last_modified,
            deck_id=self.onto.deck_id))
        for sheet in self.x_manager.sheets:
            if self.is_running:
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
        # import nodes in sheet
        try:
            for node in self.x_manager.sheets[sheet_id].nodes.values():
                self.read_node_if_concept(node=node)
        except MapError as error_info:
            self.log.append(error_info.message)
            self.is_running = False
        # import edges in sheet
        for edge in self.x_manager.sheets[sheet_id].edges.values():
            if self.is_running:
                self.read_edge(edge=edge)
            else:
                return

    def read_node_if_concept(self, node: XmindNode) -> None:
        """
        If the node is not empty:
        - adds a concept for the node to the ontology
        - registers relations from this node to its parent nodes for the ontology
        - adds the node's data to the respective lists for finishing the import
        :param node: the node to import
        """
        if not node.is_empty:
            # register the concept for this node in the ontology
            self.nodes_4_concepts.append(node.dto)
            # register relations of this node to its parent nodes
            if node.parent_edge is not None:
                smr_triples = [SmrTripleDto(parent_node_id=parent_node.id, edge_id=node.parent_edge.id,
                                            child_node_id=node.id) for parent_node in node.parent_edge.parent_nodes]
                self.smr_triples_2_import.extend(smr_triples)
            # register data for this node for the smr world
            self._append_topic_data(topic=node, type_is_node=True)

    def read_edge(self, edge: XmindEdge) -> None:
        """
        - if the edge is not empty:
            - adds the edge to the list of edges to make notes of
            - adds the relationship property to the ontology
        - connects all parent- and child nodes using the relationship property and adds the triples to the list for
        the smr world
        - adds the edge's data to the lists for finishing the import
        :param edge: tag that represents the edge to be imported
        """
        # if the edge is not empty, add it to the list of edges to make notes from and get the relation class name
        if not edge.is_empty:
            # add edge to edge ids to make notes of
            self.edge_ids_2_make_notes_of.add(edge.id)
        # add edge data to the respective lists
        self._append_topic_data(topic=edge, type_is_node=False)

    def _append_topic_data(self, topic: Union[XmindNode, XmindEdge], type_is_node: bool):
        """
        If needed, appends the topic's media uris to the respective list, gets the topic's TopicDto and adds it to
        the list nodes_2_import or edges_2_import
        :param topic: either an XmindNode or an XmindEdge for which to add the data to the respective lists
        :param type_is_node: Whether the topic for which to record the data is an xmind node (False means it is an edge)
        """
        # if needed, add image and media to media files to add to collection after import
        if topic.image:
            self.media_uris_2_add.append(topic.image)
        if topic.media:
            self.media_uris_2_add.append(topic.media)
        # add the edge to the list of edges to add to the smr_world
        if not type_is_node:
            self.edges_2_import.append(topic.dto)

    def finish_import(self) -> None:
        """
        - Cancels the import if something went wrong
        - otherwise:
            - Adds concepts and relations to the ontology
            - Adds media files to the anki collection
            - Adds all data to the smr world
            - Imports notes and cards from list notes_2_import
            - Saves the smr world
        """
        if not self.is_running:
            return
        self.add_media_2_anki_collection()
        self._add_entities_2_ontology()
        # Create Notes from all edges
        self.notes_2_import = self.smr_world.generate_notes(self.col, edge_ids=self.edge_ids_2_make_notes_of)
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
        self.col.decks.select(self.onto.deck_id)
        deck = self.col.decks.get(self.onto.deck_id)
        deck['mid'] = self.model['id']
        self.col.decks.save(deck)
        self.model['did'] = self.onto.deck_id
        self.col.models.save(self.model)
        self.importNotes(list(self.notes_2_import.values()))
        # Link imported notes to edges
        self.smr_world.add_or_replace_smr_notes(self.smr_notes_2_add)
        # remove log entries informing about duplicate fields
        self.log = [self.log[-1]]

    def _add_entities_2_ontology(self):
        """
        Adds all the nodes from which we want to generate concepts to the ontology and connects them with the
        respective edges
        """
        # Add all files to the smr world
        self.smr_world.add_or_replace_xmind_files(self.files_2_import)
        # Add all sheets to the smr world
        self.smr_world.add_xmind_sheets(self.sheets_2_import)
        # Add all media and images to the smr world
        self.smr_world.add_xmind_media_to_anki_files(self.media_2_anki_files_2_import)
        # add concepts to ontology
        self.onto.add_concepts_from_nodes(self.nodes_4_concepts)
        # add relations to ontology
        self.onto.add_relations_from_edges(self.edges_2_import)
        # connect concepts in triples
        storid_triples = self.smr_world.get_storid_triples_from_smr_triples(self.smr_triples_2_import)
        for triple in storid_triples:
            self.onto.connect_concepts(parent_storid=triple[0], relation_storid=triple[1], child_storid=triple[2])
        # Add all triples to the smr world
        self.smr_world.add_smr_triples(self.smr_triples_2_import)
