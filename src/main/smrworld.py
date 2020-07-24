import os
from typing import List, TextIO

from bs4 import Tag
from main.consts import ADDON_PATH, USER_PATH
from main.dto.nodecontentdto import NodeContentDTO
from owlready2.namespace import World
from main.xmanager import XManager

FILE_NAME = 'smrworld.sqlite3'
SQL_FILE_NAME = 'smrworld.sql'
ANKI_COLLECTION_DB_NAME = "anki_collection"


class SmrWorld(World):
    """
    Class for managing all the data required by SMR
    """

    def __init__(self):
        super().__init__()
        self.set_backend(filename=os.path.join(USER_PATH, FILE_NAME))
        self.graph.execute('PRAGMA foreign_keys = ON')
        self.save()

    def set_up(self) -> None:
        """
        Sets up SMR's database architecture. Use this method once to set up the database for the first time.
        """
        sql_file: TextIO = open(os.path.join(ADDON_PATH, SQL_FILE_NAME), 'r')
        sql_code: List[str] = sql_file.read().split(';')
        sql_file.close()
        for statement in sql_code:
            self.graph.execute(statement)
        self.save()

    def add_ontology_lives_in_deck(self, ontology_base_iri: str, deck_id: str) -> None:
        """
        Registers a deck for an imported ontology
        :param ontology_base_iri: base_iri of the imported ontology
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        c = self.graph.execute("SELECT c FROM ontologies WHERE iri = '{}'".format(ontology_base_iri)).fetchone()[0]
        self.graph.execute("INSERT INTO ontology_lives_in_deck VALUES (?, ?)", (int(deck_id), c))

    def add_xmind_file(self, x_manager: XManager, deck_id: str) -> None:
        """
        Adds an entry for an xmind file to the relation xmind_files
        :param x_manager: the x_manager that manages the file
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        self.graph.execute("INSERT INTO main.xmind_files VALUES (?, ?, ?, ?)", (
            x_manager.get_file(), x_manager.get_map_last_modified(), x_manager.get_file_last_modified(), int(deck_id)))

    def add_xmind_sheet(self, x_manager: XManager, sheet: str) -> None:
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param x_manager: the x_manager that manages the file
        :param sheet: the name of the sheet to import
        """
        self.graph.execute("INSERT INTO main.xmind_sheets VALUES (?, ?, ?)", (
            x_manager.get_sheet_id(sheet), x_manager.get_file(), x_manager.get_sheet_last_modified(sheet)))

    def add_xmind_node(self, node: Tag, node_content: NodeContentDTO, ontology_storid: int, sheet_id: str,
                       order_number: int) -> None:
        """
        Adds an entry for an xmind node to the relation xmind_nodes
        :param node: the tag representing the node to add
        :param node_content: the node's content as a dictionary
        :param ontology_storid: the storid of the concept in the ontology that represents the node
        :param sheet_id: xmind id of the sheet that contains the node
        :param order_number: order number of the node with respect to its siblings 
        """
        self.graph.execute(
            "INSERT INTO main.xmind_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                node['id'], sheet_id, node_content.title, node_content.image,
                node_content.media, ontology_storid, node['timestamp'], order_number))

    def add_xmind_edge(self, edge: Tag, edge_content: NodeContentDTO, sheet_id: str, order_number: int,
                       ontology_storid: int) -> None:
        """
        Adds an entry for an xmind edge to the relation xmind_edges
        :param edge: the tag representing the edge to add
        :param edge_content: the edge's content as a dictionary
        :param sheet_id: xmind id of the sheet that contains the edge
        :param order_number: order number of the edge with respect to its siblings
        :param ontology_storid: storid of the respective relation in the ontology
        """
        self.graph.execute("INSERT INTO main.xmind_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            edge['id'], sheet_id, edge_content.title, edge_content.image,
            edge_content.media, ontology_storid, edge['timestamp'], order_number))

    def add_smr_triple(self, parent_node_id: str, edge_id: str, child_node_id: str, card_id: int) -> None:
        """
        adds an entry for a triple of parent node, edge, and child node to the relation smr_triples
        :param parent_node_id: the parent node's xmind id
        :param edge_id: the edge's xmind id
        :param child_node_id: the child node's xmind id
        :param card_id: anki's id for the card that corresponds to this triple
        """
        self.graph.execute("INSERT INTO main.smr_triples VALUES (?, ?, ?, ?)",
                           (parent_node_id, edge_id, child_node_id, card_id))

    def attach_anki_collection(self, anki_collection):
        self.graph.execute("ATTACH DATABASE '{anki_collection_path}' as {anki_collection_db_name}".format(
            anki_collection_path=anki_collection.path, anki_collection_db_name=ANKI_COLLECTION_DB_NAME))
