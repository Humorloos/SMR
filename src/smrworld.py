import os
from typing import List, TextIO

from bs4 import Tag
from consts import ADDON_PATH, USER_PATH
from owlready2.namespace import World
from xmanager import XManager

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

    def set_up(self):
        """
        Sets up SMR's database architecture. Use this method once to set up the database for the first time.
        """
        sql_file: TextIO = open(os.path.join(ADDON_PATH, SQL_FILE_NAME), 'r')
        sql_code: List[str] = sql_file.read().split(';')
        sql_file.close()
        for statement in sql_code:
            self.graph.execute(statement)
        self.save()

    def add_ontology_lives_in_deck(self, ontology_base_iri: str, deck_id: str):
        """
        Registers a deck for an imported ontology
        :param ontology_base_iri: base_iri of the imported ontology
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        c = self.graph.execute("SELECT c FROM ontologies WHERE iri = '{}'".format(ontology_base_iri)).fetchone()[0]
        self.graph.execute(
            "INSERT INTO ontology_lives_in_deck VALUES ({deck_id}, {c})".format(deck_id=int(deck_id), c=c))

    def add_xmind_file(self, x_manager: XManager, deck_id: str):
        """
        Adds an entry for an xmind file to the relation xmind_files
        :param x_manager: the x_manager that manages the file
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        self.graph.execute(
            "INSERT INTO main.xmind_files VALUES ('{path}', {map_last_modified}, {file_last_modified}, "
            "{deck_id})".format(
                path=x_manager.get_file(), map_last_modified=x_manager.get_map_last_modified(),
                file_last_modified=x_manager.get_file_last_modified(), deck_id=int(deck_id)))

    def add_xmind_sheet(self, x_manager: XManager, sheet: str):
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param x_manager: the x_manager that manages the file
        :param sheet: the name of the sheet to import
        """
        self.graph.execute("INSERT INTO main.xmind_sheets VALUES ('{sheet_id}', '{path}', {last_modified})".format(
            sheet_id=x_manager.get_sheet_id(sheet), path=x_manager.get_file(),
            last_modified=x_manager.get_sheet_last_modified(sheet)))

    def add_xmind_node(self, node: Tag, node_content: dict, ontology_storid: int, sheet_id: str, order_number: int):
        """
        Adds an entry for an xmind node to the relation xmind_nodes
        :param node: the tag representing the node to add
        :param node_content: the node's content as a dictionary
        :param ontology_storid: the storid of the concept in the ontology that represents the node
        :param sheet_id: xmind id of the sheet that contains the node
        :param order_number: order number of the node with respect to its siblings 
        """
        self.graph.execute(
            "INSERT INTO main.xmind_nodes VALUES ('{node_id}', '{sheet_id}', '{title}', '{image}', '{link}', "
            "{ontology_storid}, {last_modified}, {order_number})".format(node_id=node['id'], sheet_id=sheet_id,
                                                                         title=node_content['content'],
                                                                         image=node_content['media']['image'],
                                                                         link=node_content['media']['media'],
                                                                         ontology_storid=ontology_storid,
                                                                         last_modified=node['timestamp'],
                                                                         order_number=order_number))

    def add_xmind_edge(self, edge: Tag, edge_content: dict, sheet_id: str, order_number: int):
        """
        Adds an entry for an xmind edge to the relation xmind_edges
        :param edge: the tag representing the edge to add
        :param edge_content: the edge's content as a dictionary
        :param sheet_id: xmind id of the sheet that contains the edge
        :param order_number: order number of the edge with respect to its siblings
        """
        self.graph.execute(
            "INSERT INTO main.xmind_edges VALUES ('{edge_id}', '{sheet_id}', {last_modified}, '{title}', '{image}', "
            "'{link}', {order_number})".format(edge_id=edge['id'], sheet_id=sheet_id, title=edge_content['content'],
                                               image=edge_content['media']['image'],
                                               link=edge_content['media']['media'], last_modified=edge['timestamp'],
                                               order_number=order_number))

    def attach_anki_collection(self, anki_collection):
        self.graph.execute("ATTACH DATABASE '{anki_collection_path}' as {anki_collection_db_name}".format(
            anki_collection_path=anki_collection.path, anki_collection_db_name=ANKI_COLLECTION_DB_NAME))
