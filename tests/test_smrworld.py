from sqlite3 import IntegrityError

import XmindImport.tests.constants as cts
import pytest


def test_set_up(empty_smr_world, empty_anki_collection):
    # given
    expected_tables = ["store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources",
                       "ontology_lives_in_deck", "xmind_files", "xmind_sheets", "xmind_edges", "smr_notes",
                       "xmind_nodes", "smr_triples"]
    expected_databases = [0]
    cut = empty_smr_world
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
    expected_entry = (cts.EXAMPLE_MAP_PATH, 1594823958217, 1594823958.8585837, int(cts.TEST_DECK_ID))
    # given
    cut = smr_world_for_tests
    # when
    cut.add_xmind_file(x_manager=x_manager, deck_id=cts.TEST_DECK_ID)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_files").fetchall())[1] == expected_entry


def test_add_xmind_sheet(smr_world_for_tests, x_manager):
    # given
    expected_entry = ('2485j5qgetfevlt00vhrn53961', cts.TEST_FILE_PATH, 1594823927933)
    cut = smr_world_for_tests
    manager = x_manager
    manager._file = cts.TEST_FILE_PATH
    # when
    cut.add_xmind_sheet(x_manager=manager, sheet='biological psychology')
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_sheets").fetchall())[1] == expected_entry


def test_add_xmind_sheet_wrong_path(smr_world_for_tests, x_manager):
    # given
    cut = smr_world_for_tests
    manager = x_manager
    manager._file = 'wrong path'
    # then
    with pytest.raises(IntegrityError):
        # when
        cut.add_xmind_sheet(x_manager=manager, sheet='biological psychology')


def test_add_xmind_node(smr_world_for_tests, x_manager):
    # given
    expected_entry = (
        '4r6avbt0pbuam4fg07jod0ubec', cts.TEST_SHEET_ID, 'neurotransmitters',
        'attachments/629d18n2i73im903jkrjmr98fg.png',
        'None', 153, 1578314907411, 1)
    cut = smr_world_for_tests
    # when
    cut.add_xmind_node(node=x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_XMIND_ID),
                       node_content=cts.NEUROTRANSMITTERS_NODE_CONTENT, ontology_storid=cts.TEST_CONCEPT_STORID,
                       sheet_id=cts.TEST_SHEET_ID, order_number=1)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_nodes").fetchall())[0] == expected_entry


def test_add_xmind_edge(smr_world_for_tests, x_manager):
    # given
    expected_entry = ('485fcs7jl72gtqesace4v8igf0', cts.TEST_SHEET_ID, 1573032291149, 'types', 'None', 'None', 1)
    manager = x_manager
    edge = manager.get_tag_by_id("485fcs7jl72gtqesace4v8igf0")
    cut = smr_world_for_tests
    # when
    cut.add_xmind_edge(edge=edge, edge_content=manager.get_node_content(edge), sheet_id=cts.TEST_SHEET_ID,
                       order_number=1)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_edges").fetchall())[0] == expected_entry
