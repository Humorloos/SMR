import os

import pytest
import smrworld
from XmindImport.tests.constants import TEST_DECK_ID, EXAMPLE_MAP_PATH


@pytest.fixture
def smr_world():
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    test_world = "testworld.sqlite3"
    standard_world = smrworld.FILE_NAME
    smrworld.FILE_NAME = test_world
    yield smrworld.SmrWorld()
    smrworld.FILE_NAME = standard_world
    os.unlink(os.path.join(smrworld.USER_PATH, test_world))


def test_set_up(smr_world, empty_anki_collection):
    # given
    expected_tables = ["store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources",
                       "ontology_lives_in_deck", "xmind_files", "xmind_sheets", "xmind_edges", "smr_notes",
                       "xmind_nodes", "smr_triples"]
    expected_databases = [0]
    cut = smr_world
    # when
    cut.set_up()
    smrworld_tables = [r[0] for r in
                       cut.graph.execute("SELECT name from sqlite_master where type = 'table'").fetchall()]
    smrworld_databases = [r[0] for r in cut.graph.execute('PRAGMA database_list').fetchall()]
    cut.close()
    # then
    assert smrworld_tables == expected_tables
    assert smrworld_databases == expected_databases


def test_add_xmind_file(smr_world_for_tests, x_manager):
    expected_entry = (EXAMPLE_MAP_PATH, 1579197475503, 1583751104.0, int(TEST_DECK_ID))
    # given
    cut = smr_world_for_tests
    # when
    cut.add_xmind_file(x_manager=x_manager, deck_id=TEST_DECK_ID)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_files").fetchall())[0] == expected_entry
