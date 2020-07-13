import os

from consts import ADDON_PATH, USER_PATH
from owlready2.namespace import World

FILE_NAME = 'smrworld.sqlite3'
SQL_FILE_NAME = 'smrworld.sql'
ANKI_COLLECTION_DB_NAME = "anki_collection"


class SmrWorld(World):
    """
    Class for managing all the data required by SMR
    """

    def __init__(self, anki_collection):
        super().__init__()
        self.set_backend(filename=os.path.join(USER_PATH, FILE_NAME))
        self.graph.execute("ATTACH DATABASE '{anki_collection_path}' as {anki_collection_db_name}".format(
            anki_collection_path=anki_collection.path, anki_collection_db_name=ANKI_COLLECTION_DB_NAME))

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
