from sqlite3 import IntegrityError

import test.constants as cts
import pytest
from main.xmanager import get_node_content


def test_set_up(empty_smr_world, empty_anki_collection):
    # given
    expected_tables = ["store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources",
                       "ontology_lives_in_deck", "xmind_files", "xmind_sheets", "xmind_media_to_anki_files",
                       "xmind_edges", "smr_notes", "xmind_nodes", "smr_triples"]
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
    expected_entry = (cts.EXAMPLE_MAP_PATH, 1595671089759, 1595687290.0987637, int(cts.TEST_DECK_ID))
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


def test_add_xmind_node_with_media_hyperlink(smr_world_for_tests, x_manager):
    # given
    expected_entry = (cts.MEDIA_HYPERLINK_XMIND_ID, cts.TEST_SHEET_ID, '', None,
                      "C:/Users/lloos/OneDrive - bwedu/Projects/AnkiAddon/anki-addon-dev/addons21/XmindImport"
                      "/resources/serotonin.mp3", 153, 1595671089759, 1)
    cut = smr_world_for_tests
    # when
    cut.add_xmind_node(node=x_manager.get_tag_by_id(cts.MEDIA_HYPERLINK_XMIND_ID),
                       node_content=cts.MEDIA_HYPERLINK_NODE_CONTENT, ontology_storid=cts.TEST_CONCEPT_STORID,
                       sheet_id=cts.TEST_SHEET_ID, order_number=1)
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_nodes WHERE node_id = '{}'".format(cts.MEDIA_HYPERLINK_XMIND_ID)).fetchall())[
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
    test_edge_id = 'edge id'
    expected_entry = ('node id', test_edge_id, 'node id2', None)
    cut = smr_world_for_tests
    # when
    cut.add_smr_triple(parent_node_id=cts.TEST_CONCEPT_NODE_ID, edge_id=cts.TEST_RELATION_EDGE_ID,
                       child_node_id=cts.TEST_CONCEPT_2_NODE_ID, card_id=None)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.smr_triples WHERE edge_id = '{}'".format(
        test_edge_id)).fetchall())[0] == expected_entry


def test_get_smr_note_reference_data(smr_world_for_tests):
    # when
    reference = smr_world_for_tests.get_smr_note_reference_data(cts.PRONOUNCIATION_EDGE_XMIND_ID)
    # then
    assert reference == [('biological psychology', 'investigates'), ('information transfer and processing', 'requires'),
                         ('neurotransmitters <img src="attachments629d18n2i73im903jkrjmr98fg.png">', 'types'),
                         ('biogenic amines', ' <img src="attachments09r2e442o8lppjfeblf7il2rmd.png">'),
                         ('Serotonin', 'pronounciation')]


def test_get_smr_note_reference_data_with_edge_following_multiple_nodes(smr_world_for_tests):
    # when
    reference = smr_world_for_tests.get_smr_note_reference_data(cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert reference == [('biological psychology', 'investigates'),
                         ('information transfer and processing', 'modulated by'), ('enzymes', 'example'),
                         ('MAO', 'splits up'), ('dopamine,adrenaline,Serotonin,noradrenaline', 'are')]


def test_get_smr_note_reference_data_with_media(smr_world_for_tests):
    # when
    reference = smr_world_for_tests.get_smr_note_reference_data(cts.EDGE_WITH_MEDIA_XMIND_ID)
    # then
    assert reference == [('biological psychology', 'investigates'), ('perception', ''),
                         ('Pain', 'some media edge title [sound:somemedia.mp3]')]


def test_get_smr_note_question_field_media_edge(smr_world_for_tests):
    # when
    question = smr_world_for_tests.get_smr_note_question_field(cts.EDGE_WITH_MEDIA_XMIND_ID)
    # then
    assert question == 'some media edge title [sound:somemedia.mp3]'


def test_get_smr_note_question_field_only_image(smr_world_for_tests):
    # when
    question = smr_world_for_tests.get_smr_note_question_field("08eq1rdricsp1nt1b7aa181sq4")
    # then
    assert question == ' <img src="attachments09r2e442o8lppjfeblf7il2rmd.png">'


def test_get_smr_note_answer_fields(smr_world_for_tests):
    # when
    answers = smr_world_for_tests.get_smr_note_answer_fields(cts.EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert answers == ['Serotonin', 'dopamine', 'adrenaline', 'noradrenaline']


def test_get_smr_note_answer_fields_image(smr_world_for_tests):
    # when
    answers = smr_world_for_tests.get_smr_note_answer_fields("730ahk5oc4himfrdvkqc5ci1o2")
    # then
    assert answers == ['neurotransmitters <img src="attachments629d18n2i73im903jkrjmr98fg.png">']


def test_get_smr_note_answer_fields_media(smr_world_for_tests):
    # when
    answers = smr_world_for_tests.get_smr_note_answer_fields("4vfsmbd1fmn6s0tqmlj4cei7pe")
    # then
    assert answers == [' [sound:attachments395ke7i9a6nkutu85fcpa66as2.mp4]']


def test_get_smr_note_sort_data(smr_world_for_tests):
    # when
    sort_field_data = smr_world_for_tests.get_smr_note_sort_data(cts.PRONOUNCIATION_EDGE_XMIND_ID)
    # then
    assert sort_field_data == [(1, 2), (1, 1), (1, 1), (1, 1), (1, 2)]