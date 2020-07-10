import os
import sqlite3

import pytest
import smrworld

test_collection = "testworld.sqlite3"


@pytest.fixture()
def connection(monkeypatch):
    con = sqlite3.connect(os.path.join(smrworld.USER_PATH, test_collection))
    yield con
    con.close()
    os.unlink(os.path.join(smrworld.USER_PATH, test_collection))


def test_set_up(connection):
    # given
    expected_tables = ["store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources", "xmind_files",
                       "xmind_sheets", "xmind_edges", "smr_notes", "xmind_nodes", "smr_triples"]
    smrworld.SmrWorld.FILE_NAME = test_collection
    cut = smrworld.SmrWorld()
    # when
    cut.set_up()
    cut.close()
    cursor = connection.cursor()
    cursor.execute('SELECT name from sqlite_master where type = "table"')
    # then
    assert [e[0] for e in cursor.fetchall()] == expected_tables
