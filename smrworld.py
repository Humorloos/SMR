import os

from consts import ADDON_PATH, USER_PATH
from owlready2.namespace import World


class SmrWorld (World):
    """
    Class for managing all the data required by SMR
    """
    FILE_NAME = 'smrworld.sqlite3'
    SQL_FILE_NAME = 'smrworld.sql'

    def __init__(self):
        super().__init__()
        self.set_backend(filename=os.path.join(USER_PATH, self.FILE_NAME))

    def set_up(self):
        """
        Sets up SMR's database architecture. Use this method once to set up the database for the first time.
        """
        sql_file = open(os.path.join(ADDON_PATH, self.SQL_FILE_NAME), 'r')
        sql_code = sql_file.read().split(';')
        sql_file.close()
        for statement in sql_code:
            self.graph.execute(statement)
        self.save()
