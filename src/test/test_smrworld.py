from sqlite3 import IntegrityError, OperationalError

import pytest

import test.constants as cts
from main.dto.smrtripledto import SmrTripleDto
from main.dto.xmindfiledto import XmindFileDto
from main.dto.xmindnodedto import XmindNodeDto
from main.dto.xmindsheetdto import XmindSheetDto
from main.xmanager import get_node_content


def test_set_up(empty_smr_world, empty_anki_collection_session):
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
    # then
    assert smrworld_tables == expected_tables
    assert smrworld_databases == expected_databases


def test_add_xmind_files(smr_world_for_tests, x_manager):
    expected_entry = (cts.EXAMPLE_MAP_PATH, 1595671089759, 1595687290.0, cts.TEST_DECK_ID)
    # given
    cut = smr_world_for_tests
    # when
    cut.add_xmind_files([XmindFileDto(path=cts.EXAMPLE_MAP_PATH, map_last_modified=1595671089759,
                                      file_last_modified=1595687290.0, deck_id=cts.TEST_DECK_ID)])
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_files").fetchall())[1] == expected_entry


@pytest.fixture
def x_manager_test_file(x_manager):
    manager = x_manager
    default_file = x_manager.file
    manager._file = cts.TEST_FILE_PATH
    yield manager
    manager._file = default_file


def test_add_xmind_sheets(smr_world_for_tests, x_manager_test_file):
    # given
    expected_entry = ('2485j5qgetfevlt00vhrn53961', cts.TEST_FILE_PATH, 1595671089759)
    cut = smr_world_for_tests
    manager = x_manager_test_file
    sheet = 'biological psychology'
    entities = [XmindSheetDto(sheet_id=manager.get_sheet_id(sheet), path=manager.file,
                              last_modified=manager.get_sheet_last_modified(sheet))]
    # when
    cut.add_xmind_sheets(entities)
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_sheets").fetchall())[1] == expected_entry


@pytest.fixture
def x_manager_absent_file(x_manager):
    manager = x_manager
    default_file = x_manager.file
    manager.file = 'wrong path'
    yield manager
    manager.file = default_file


def test_add_xmind_sheet_wrong_path(smr_world_for_tests, x_manager_absent_file):
    # given
    cut = smr_world_for_tests
    manager = x_manager_absent_file
    # then
    with pytest.raises(IntegrityError):
        # when
        cut.add_xmind_sheets([XmindSheetDto(path=manager.file, sheet_id=cts.TEST_SHEET_ID, last_modified=12345)])


def test_add_xmind_nodes(smr_world_for_tests, x_manager):
    # given
    expected_entry = (cts.NEUROTRANSMITTERS_XMIND_ID, cts.TEST_SHEET_ID, 'neurotransmitters',
                      'attachments/629d18n2i73im903jkrjmr98fg.png', None, 153, 1578314907411, 1)
    # then
    verify_add_xmind_node(expected_entry, smr_world_for_tests, x_manager, cts.NEUROTRANSMITTERS_XMIND_ID,
                          cts.NEUROTRANSMITTERS_NODE_CONTENT)


def test_add_xmind_nodes_with_media_hyperlink(smr_world_for_tests, x_manager):
    # given
    expected_entry = (cts.MEDIA_HYPERLINK_XMIND_ID, cts.TEST_SHEET_ID, '', None,
                      "C:/Users/lloos/OneDrive - bwedu/Projects/AnkiAddon/anki-addon-dev/addons21/XmindImport"
                      "/resources/serotonin.mp3", 153, 1595671089759, 1)
    # then
    verify_add_xmind_node(expected_entry, smr_world_for_tests, x_manager, cts.MEDIA_HYPERLINK_XMIND_ID,
                          cts.MEDIA_HYPERLINK_NODE_CONTENT)


def verify_add_xmind_node(expected_entry, cut, x_manager, tag_id, node_content):
    # given
    node = x_manager.get_tag_by_id(tag_id)
    # when
    cut.add_xmind_nodes([XmindNodeDto(
        node_id=node['id'], sheet_id=cts.TEST_SHEET_ID, title=node_content.title, image=node_content.image,
        link=node_content.media, ontology_storid=cts.TEST_CONCEPT_STORID, last_modified=node['timestamp'],
        order_number=1)])
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_nodes WHERE node_id = '{}'".format(tag_id)).fetchall())[0] == expected_entry


def test_add_xmind_edges(smr_world_for_tests, x_manager):
    # given
    expected_entry = (cts.TYPES_EDGE_XMIND_ID, cts.TEST_SHEET_ID, 'types', None, None, cts.TEST_RELATION_STORID,
                      1573032291149, 1)
    manager = x_manager
    edge = manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID)
    edge_content = get_node_content(edge)
    cut = smr_world_for_tests
    # when
    cut.add_xmind_edges([XmindNodeDto(
        node_id=edge['id'], sheet_id=cts.TEST_SHEET_ID,
        title=edge_content.title, image=edge_content.image, link=edge_content.media,
        ontology_storid=cts.TEST_RELATION_STORID, last_modified=edge['timestamp'], order_number=1)])
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_edges WHERE edge_id = '{}'".format(cts.TYPES_EDGE_XMIND_ID)).fetchall())[
               0] == expected_entry


def test_add_smr_triples(smr_world_for_tests):
    # given
    test_edge_id = 'edge id'
    expected_entry = ('node id', test_edge_id, 'node id2', None)
    cut = smr_world_for_tests
    # when
    cut.add_smr_triples([SmrTripleDto(
        parent_node_id=cts.TEST_CONCEPT_NODE_ID, edge_id=cts.TEST_RELATION_EDGE_ID,
        child_node_id=cts.TEST_CONCEPT_2_NODE_ID)])
    # then
    assert list(cut.graph.execute("SELECT * FROM main.smr_triples WHERE edge_id = '{}'".format(
        test_edge_id)).fetchall())[0] == expected_entry


def test_get_smr_note_references(smr_world_for_tests):
    # when
    reference = smr_world_for_tests.get_smr_note_references([
        cts.PRONOUNCIATION_EDGE_XMIND_ID, cts.EDGE_WITH_MEDIA_XMIND_ID, cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID])
    # then
    assert reference == {
        '4s27e1mvsb5jqoiuaqmnlo8m71': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>requires: neurotransmitters <img '
                                      'src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic '
                                      'amines</li><li><img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: '
                                      'Serotonin</li>',
        '6iivm8tpoqj2c0euaabtput14l': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits '
                                      'up: Serotonin, dopamine, adrenaline, noradrenaline</li>',
        '7ite3obkfmbcasdf12asd123ga': 'biological psychology<li>investigates: perception</li><li>Pain</li>'}


def test_get_smr_note_question_field_media_edge(smr_world_for_tests):
    # when
    question = smr_world_for_tests.get_smr_note_question_field(cts.EDGE_WITH_MEDIA_XMIND_ID)
    # then
    assert question == 'some media edge title [sound:somemedia.mp3]'


def test_get_smr_note_question_field_only_image(smr_world_for_tests):
    # when
    question = smr_world_for_tests.get_smr_note_question_field("08eq1rdricsp1nt1b7aa181sq4")
    # then
    assert question == '<img src="attachments09r2e442o8lppjfeblf7il2rmd.png">'


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
    assert answers == ['[sound:attachments395ke7i9a6nkutu85fcpa66as2.mp4]']


def test_get_smr_note_sort_data(smr_world_for_tests):
    # when
    sort_field_data = smr_world_for_tests.get_smr_note_sort_data(cts.PRONOUNCIATION_EDGE_XMIND_ID)
    # then
    assert sort_field_data == [(1, 2), (1, 1), (1, 1), (1, 1), (1, 2)]


def test_update_smr_triples_card_ids(smr_world_for_tests, collection_4_migration):
    # given
    cut = smr_world_for_tests
    # when
    cut.update_smr_triples_card_ids(data=[(1581184936757, 1)], collection=collection_4_migration)
    # then
    assert cut.graph.execute("select card_id from smr_triples where edge_id = ?",
                             ('4kdqkutdha46uns1j8jndi43ht',)).fetchall() == [(1581184936819,), (None,)]


def test_attach_anki_collection(smr_world_for_tests, empty_anki_collection_session):
    # when
    smr_world_for_tests.attach_anki_collection(empty_anki_collection_session)
    # then
    assert len(smr_world_for_tests.graph.db.execute("select * from main.smr_triples, "
                                                    "anki_collection.deck_config").fetchall()) > 0
    # when
    smr_world_for_tests.detach_anki_collection(empty_anki_collection_session)
    # then
    with pytest.raises(OperationalError) as exception_info:
        smr_world_for_tests.graph.db.execute("select * from main.smr_triples, anki_collection.deck_config").fetchall()
    assert exception_info.value.args[0] == 'no such table: anki_collection.deck_config'
    assert len(empty_anki_collection_session.db.execute('select * from main.deck_config')) == 1
