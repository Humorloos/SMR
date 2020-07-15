import os

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

    def set_up(self):
        """
        Sets up SMR's database architecture. Use this method once to set up the database for the first time.
        """
        sql_file = open(os.path.join(ADDON_PATH, SQL_FILE_NAME), 'r')
        sql_code = sql_file.read().split(';')
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
            "INSERT INTO xmind_files VALUES ('{path}', {map_last_modified}, {file_last_modified}, {deck_id})".format(
                path=x_manager.file, map_last_modified=x_manager.get_map_last_modified(),
                file_last_modified=x_manager.get_file_last_modified(), deck_id=int(deck_id)))

    def add_xmind_sheet(self, x_manager: XManager, deck_id: str):
        """
        Adds an entry for an xmind sheet to the relation xmind_sheets
        :param x_manager: the x_manager that manages the file
        :param deck_id: the id of the deck from anki (number in form of a string)
        """
        return

    def attach_anki_collection(self, anki_collection):
        self.graph.execute("ATTACH DATABASE '{anki_collection_path}' as {anki_collection_db_name}".format(
            anki_collection_path=anki_collection.path, anki_collection_db_name=ANKI_COLLECTION_DB_NAME))
