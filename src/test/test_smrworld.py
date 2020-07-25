from sqlite3 import IntegrityError

import test.constants as cts
import pytest
from main.xmanager import get_node_content


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
    expected_entry = (cts.EXAMPLE_MAP_PATH, 1595671089759, 1595671098.9155583, int(cts.TEST_DECK_ID))
    # given
    cut = smr_world_for_tests
    # when
    cut.add_xmind_file(x_manager=x_manager, deck_id=cts.TEST_DECK_ID)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_files").fetchall())[1] == expected_entry


def test_add_xmind_sheet(smr_world_for_tests, x_manager):
    # given
    expected_entry = ('2485j5qgetfevlt00vhrn53961', cts.TEST_FILE_PATH, 1595671089759)
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
    expected_entry = (cts.NEUROTRANSMITTERS_XMIND_ID, cts.TEST_SHEET_ID, 'neurotransmitters',
                      'attachments/629d18n2i73im903jkrjmr98fg.png', None, 153, 1578314907411, 1)
    cut = smr_world_for_tests
    # when
    cut.add_xmind_node(node=x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_XMIND_ID),
                       node_content=cts.NEUROTRANSMITTERS_NODE_CONTENT, ontology_storid=cts.TEST_CONCEPT_STORID,
                       sheet_id=cts.TEST_SHEET_ID, order_number=1)
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_nodes WHERE node_id = '{}'".format(cts.NEUROTRANSMITTERS_XMIND_ID)).fetchall())[
               0] == expected_entry


def test_add_xmind_edge(smr_world_for_tests, x_manager):
    # given
    expected_entry = (cts.TYPES_EDGE_XMIND_ID, cts.TEST_SHEET_ID, 'types', None, None, cts.TEST_RELATION_STORID,
                      1573032291149, 1)
    manager = x_manager
    edge = manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID)
    cut = smr_world_for_tests
    # when
    cut.add_xmind_edge(edge=edge, edge_content=get_node_content(edge), sheet_id=cts.TEST_SHEET_ID,
                       order_number=1, ontology_storid=cts.TEST_RELATION_STORID)
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_edges WHERE edge_id = '{}'".format(cts.TYPES_EDGE_XMIND_ID)).fetchall())[
               0] == expected_entry


def test_add_smr_triple(smr_world_for_tests):
    # given
    expected_entry = ('node id', 'edge id', 'node id2', None)
    cut = smr_world_for_tests
    # when
    cut.add_smr_triple(parent_node_id=cts.TEST_CONCEPT_NODE_ID, edge_id=cts.TEST_RELATION_EDGE_ID,
                       child_node_id=cts.TEST_CONCEPT_2_NODE_ID, card_id=None)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.smr_triples").fetchall())[0] == expected_entry
