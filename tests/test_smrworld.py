import os

import pytest
import smrworld

test_collection = "testworld.sqlite3"


@pytest.fixture
def clean_up():
    yield
    os.unlink(os.path.join(smrworld.USER_PATH, test_collection))


def test_set_up(empty_anki_collection, clean_up):
    # given
    expected_tables = ["store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources", "xmind_files",
                       "xmind_sheets", "xmind_edges", "smr_notes", "xmind_nodes", "smr_triples"]
    expected_databases = [0, 2]
    smrworld.FILE_NAME = test_collection
    cut = smrworld.SmrWorld(anki_collection=empty_anki_collection)
    # when
    cut.set_up()
    smrworld_tables = [r[0] for r in
                       cut.graph.execute('SELECT name from sqlite_master where type = "table"').fetchall()]
    smrworld_databases = [r[0] for r in cut.graph.execute('PRAGMA database_list').fetchall()]
    cut.close()
    # then
    assert smrworld_tables == expected_tables
    assert smrworld_databases == expected_databases
