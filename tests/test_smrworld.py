from sqlite3 import IntegrityError, OperationalError

import pytest
from assertpy import assert_that

from smr.dto.smrtripledto import SmrTripleDto
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindsheetdto import XmindSheetDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import CHILD_RELATION_NAME, PARENT_RELATION_NAME
from smr.smrworld import sort_id_from_order_number
from smr.xontology import XOntology
from tests import constants as cts


def test_set_up(empty_smr_world, empty_anki_collection_session):
    # given
    expected_tables = {"store", "objs", "datas", "ontologies", "ontology_alias", "prop_fts", "resources",
                       "ontology_lives_in_deck", "xmind_files", "xmind_sheets", "xmind_media_to_anki_files",
                       "xmind_edges", "smr_notes", "xmind_nodes", "smr_triples"}
    expected_databases = {0}
    cut = empty_smr_world
    # when
    cut.set_up()
    smrworld_tables = {r[0] for r in
                       cut.graph.execute("SELECT name from sqlite_master where type = 'table'").fetchall()}
    smrworld_databases = {r[0] for r in cut.graph.execute('PRAGMA database_list').fetchall()}
    # then
    assert smrworld_tables == expected_tables
    assert smrworld_databases == expected_databases


def test_add_or_replace_xmind_files(smr_world_4_tests, x_manager):
    expected_entry = (cts.RESOURCES_PATH, cts.NAME_EXAMPLE_MAP, 1595671089759, 1595687290.0, cts.TEST_DECK_ID)
    # given
    cut = smr_world_4_tests
    # when
    cut.add_or_replace_xmind_files([XmindFileDto(
        directory=cts.RESOURCES_PATH, file_name=cts.NAME_EXAMPLE_MAP, map_last_modified=1595671089759,
        file_last_modified=1595687290.0, deck_id=cts.TEST_DECK_ID)])
    # then
    assert list(cut.graph.execute("SELECT * FROM main.xmind_files").fetchall())[1] == expected_entry


def test_add_or_replace_xmind_files_replace(smr_world_4_tests, x_manager):
    # given
    cut = smr_world_4_tests
    xmind_file = cts.TEST_XMIND_FILE
    mod = 50.0
    xmind_file.file_last_modified = mod
    # when
    cut.add_or_replace_xmind_files([xmind_file])
    # then
    assert cut.get_xmind_files_in_decks()[cts.TEST_DECK_ID][0].file_last_modified == mod


@pytest.fixture
def x_manager_test_file(x_manager):
    manager = x_manager
    default_file = x_manager.file
    manager._file = cts.TEST_FILE_PATH
    yield manager
    manager._file = default_file


def test_add_xmind_sheets(smr_world_4_tests):
    # given
    cut = smr_world_4_tests
    sheet_id = 'new_sheet_id'
    file_directory = cts.TEST_FILE_DIRECTORY
    file_name = cts.TEST_FILE_NAME
    entities = [
        XmindSheetDto(sheet_id=sheet_id, file_directory=file_directory, file_name=file_name, last_modified=12345)]
    # when
    cut.add_xmind_sheets(entities)
    # then
    sheet_entity = list(cut.graph.execute(f"SELECT * FROM main.xmind_sheets WHERE sheet_id = '{sheet_id}'").fetchone())
    assert sheet_entity[0] == sheet_id
    assert sheet_entity[2] == file_directory
    assert sheet_entity[3] == file_name


@pytest.fixture
def x_manager_absent_file(x_manager):
    manager = x_manager
    default_file = x_manager.file
    manager.file = 'wrong path'
    yield manager
    manager.file = default_file


def test_add_xmind_sheet_wrong_path(smr_world_4_tests, x_manager_absent_file):
    # given
    cut = smr_world_4_tests
    manager = x_manager_absent_file
    # then
    with pytest.raises(IntegrityError):
        # when
        directory, file_name = manager.get_directory_and_file_name()
        cut.add_xmind_sheets([XmindSheetDto(
            sheet_id=cts.TEST_SHEET_ID, file_directory=directory, file_name=file_name, last_modified=12345)])


def test_add_or_replace_xmind_nodes(smr_world_4_tests, x_manager):
    # given
    # noinspection PyTypeChecker
    expected_entry = XmindTopicDto(node_id=cts.NEUROTRANSMITTERS_NODE_ID, title='neurotransmitters',
                                   image='attachments/629d18n2i73im903jkrjmr98fg.png', link=None)
    # then
    verify_add_xmind_node(expected_entry, smr_world_4_tests, x_manager, cts.NEUROTRANSMITTERS_NODE_ID,
                          cts.NEUROTRANSMITTERS_NODE_CONTENT)


def test_add_or_replace_xmind_nodes_replace(smr_world_4_tests, x_manager):
    # given
    node = cts.TEST_XMIND_NODE
    new_title = 'different title'
    node.content = TopicContentDto(image=cts.TEST_EDGE_IMAGE, media=cts.TEST_EDGE_MEDIA, title=new_title)
    cut = smr_world_4_tests
    # when
    cut.add_or_replace_xmind_nodes([node])
    # then
    new_entry = XmindTopicDto(*cut.graph.execute(
        f"select * from xmind_nodes where node_id = '{node.node_id}'").fetchone())
    assert new_entry.image == cts.TEST_EDGE_IMAGE
    assert new_entry.link == cts.TEST_EDGE_MEDIA
    assert new_entry.title == new_title


def verify_add_xmind_node(expected_entry, cut, x_manager, tag_id, node_content):
    # given
    node = x_manager.get_node_by_id(tag_id)
    # when
    cut.add_or_replace_xmind_nodes([XmindTopicDto(
        node_id=node.id, sheet_id=cts.TEST_SHEET_ID, title=node_content.title, image=node_content.image,
        link=node_content.media, order_number=1)])
    # then
    # noinspection PyProtectedMember
    xmind_node = cut._get_records("SELECT * FROM main.xmind_nodes WHERE node_id = '{}'".format(tag_id))[0]
    assert xmind_node.image == expected_entry.image
    assert xmind_node.title == expected_entry.title
    assert xmind_node.node_id == expected_entry.node_id
    assert xmind_node.link == expected_entry.link


def test_add_or_replace_xmind_edges(smr_world_4_tests, x_manager):
    # given
    expected_entry = (cts.TYPES_EDGE_ID, cts.TEST_SHEET_ID, 'types', None, None, 1, None)
    manager = x_manager
    edge = manager.get_edge_by_id(cts.TYPES_EDGE_ID)
    edge_content = edge.content
    cut = smr_world_4_tests
    # when
    cut.add_or_replace_xmind_edges([XmindTopicDto(
        node_id=edge.id, sheet_id=cts.TEST_SHEET_ID,
        title=edge_content.title, image=edge_content.image, link=edge_content.media, order_number=1)])
    # then
    assert list(cut.graph.execute(
        "SELECT * FROM main.xmind_edges WHERE edge_id = '{}'".format(cts.TYPES_EDGE_ID)).fetchall())[
               0] == expected_entry


def test_add_or_replace_xmind_edges_replace(smr_world_4_tests, x_manager):
    # given
    xmind_edge = cts.TEST_XMIND_EDGE
    new_title = 'different title'
    xmind_edge.content = TopicContentDto(image=cts.TEST_NODE_IMAGE, media=cts.TEST_NODE_MEDIA, title=new_title)
    cut = smr_world_4_tests
    # when
    cut.add_or_replace_xmind_edges([xmind_edge])
    # then
    new_entry = XmindTopicDto(*cut.graph.execute(
        f"select * from xmind_edges where edge_id = '{xmind_edge.node_id}'").fetchone())
    assert new_entry.image == cts.TEST_NODE_IMAGE
    assert new_entry.link == cts.TEST_NODE_MEDIA
    assert new_entry.title == new_title


def test_add_smr_triples(smr_world_4_tests):
    # given
    test_edge_id = 'edge id'
    expected_entry = ('node id', test_edge_id, 'node id2')
    cut = smr_world_4_tests
    # when
    cut.add_smr_triples([SmrTripleDto(
        parent_node_id=cts.TEST_CONCEPT_NODE_ID, edge_id=cts.TEST_RELATION_EDGE_ID,
        child_node_id=cts.TEST_CONCEPT_2_NODE_ID)])
    # then
    assert list(cut.graph.execute("SELECT * FROM main.smr_triples WHERE edge_id = '{}'".format(
        test_edge_id)).fetchall())[0] == expected_entry


def test_add_smr_triples_foreign_key_constraint(smr_world_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    with pytest.raises(IntegrityError) as error_info:
        cut.add_smr_triples([SmrTripleDto('this', 'is', 'invalid')])
    # then
    assert error_info.value.args[0] == 'FOREIGN KEY constraint failed'


def test_get_smr_note_question_fields(smr_world_4_tests):
    # when
    question_fields = smr_world_4_tests.get_smr_note_question_fields(
        [cts.EDGE_WITH_MEDIA_XMIND_ID, cts.EXAMPLE_IMAGE_EDGE_ID])
    # then
    assert question_fields == {
        cts.EXAMPLE_IMAGE_EDGE_ID: '<img src="attachments09r2e442o8lppjfeblf7il2rmd.png">',
        '7ite3obkfmbcasdf12asd123ga': 'some media edge title<br>[sound:somemedia.mp3]'}


def test_get_smr_note_answer_fields(smr_world_4_tests):
    # when
    edges = [cts.SPLITS_UP_EDGE_ID, "730ahk5oc4himfrdvkqc5ci1o2", "4vfsmbd1fmn6s0tqmlj4cei7pe"]
    answers = smr_world_4_tests.get_smr_note_answer_fields(edges)
    # then
    assert_that(answers).is_equal_to({
        '4vfsmbd1fmn6s0tqmlj4cei7pe': ['[sound:attachments395ke7i9a6nkutu85fcpa66as2.mp4]'],
        '61irckf1nloq42brfmbu0ke92v': ['Serotonin', 'dopamine', 'adrenaline', 'noradrenaline'],
        '730ahk5oc4himfrdvkqc5ci1o2': ['neurotransmitters<br><img src="attachments629d18n2i73im903jkrjmr98fg.png">']})


# noinspection SqlResolve
def test_attach_anki_collection(smr_world_4_tests, empty_anki_collection_session):
    # when
    smr_world_4_tests.attach_anki_collection(empty_anki_collection_session)
    # then
    assert len(smr_world_4_tests.graph.db.execute("select * from main.smr_triples, "
                                                  "anki_collection.deck_config").fetchall()) > 0
    # when
    smr_world_4_tests.detach_anki_collection(empty_anki_collection_session)
    # then
    with pytest.raises(OperationalError) as exception_info:
        smr_world_4_tests.graph.db.execute(
            "select * from main.smr_triples, anki_collection.deck_config").fetchall()
    assert exception_info.value.args[0] == 'no such table: anki_collection.deck_config'
    assert len(empty_anki_collection_session.db.execute('select * from main.deck_config')) == 1


def test_get_smr_note_tags(smr_world_4_tests, collection_4_migration):
    # when
    tag = smr_world_4_tests.get_smr_note_tags(anki_collection=collection_4_migration,
                                              edge_ids=[cts.TEST_RELATION_EDGE_ID,
                                                        cts.ARE_EDGE_ID])
    # then
    assert tag == {'6iivm8tpoqj2c0euaabtput14l': ' Example::test_file::test_sheet ',
                   'edge id': ' Example::test_file::test_sheet '}


def test_get_ontology_lives_in_deck(smr_world_with_example_map):
    # when
    ontologies_and_decks = smr_world_with_example_map.get_ontology_lives_in_deck()
    # then
    assert ontologies_and_decks[0].ontology == 1


def test_get_xmind_files_in_decks(smr_world_with_example_map):
    # when
    xmind_files_in_decks = smr_world_with_example_map.get_xmind_files_in_decks()
    # then
    files = list(xmind_files_in_decks.values())[0]
    assert files[0].directory == cts.DIRECTORY_MAPS_TEMPORARY
    assert files[0].file_name == cts.NAME_EXAMPLE_MAP
    assert files[1].file_name == cts.NAME_MAP_GENERAL_PSYCHOLOGY


def test_get_changed_smr_notes(smr_world_with_example_map, changed_collection_with_example_map):
    # when
    changed_smr_notes = smr_world_with_example_map.get_changed_smr_notes(changed_collection_with_example_map)
    # then
    assert list(changed_smr_notes.keys()) == [cts.PATH_EXAMPLE_MAP_TEMPORARY, cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY]
    values = list(changed_smr_notes.values())
    assert list(values[1].keys()) == ['general psychology']
    assert_that(values[0].keys()).contains('biological psychology', 'clinical psychology')
    example_map_sheets = changed_smr_notes[cts.PATH_EXAMPLE_MAP_TEMPORARY]
    sheet_biological_psychology = example_map_sheets['biological psychology']
    assert len(sheet_biological_psychology) == 6
    assert len(example_map_sheets['clinical psychology']) == 4
    assert len(list(values[1].values())[0]) == 1
    note_following_multiple_answers = next(edge for edge in sheet_biological_psychology.values() if
                                           edge['edge'].node_id == cts.ARE_EDGE_ID)
    assert_that(note_following_multiple_answers['parents']).contains(*cts.MULTIPLE_PARENTS_NODE_IDS)
    assert note_following_multiple_answers['answers'][1]['children'][cts.CONSIST_OF_EDGE_ID] == {
        cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID}


def test_storid_from_node_id(ontology_with_example_map):
    # when
    storid = ontology_with_example_map.world.storid_from_node_id('78k8nsh3vfibpmq73kangacbll')
    # then
    assert ontology_with_example_map.get(storid) == ontology_with_example_map.biogenic_amines


def test_storid_from_edge_id(ontology_with_example_map):
    # when
    storid = ontology_with_example_map.world.storid_from_edge_id(cts.TYPES_EDGE_ID)
    # then
    assert ontology_with_example_map.get(storid) == ontology_with_example_map.types_xrelation


def test_remove_xmind_nodes_does_not_remove_concept_if_nodes_left(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.remove_xmind_nodes([cts.SEROTONIN_1_NODE_ID])
    # then
    assert type(cut.Serotonin) == cut.Concept
    assert not cut.Serotonin.affects_xrelation
    assert not getattr(cut.Sleep, PARENT_RELATION_NAME)


def test_get_smr_note_reference_fields(smr_world_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    reference_fields = cut.get_smr_note_reference_fields(edge_ids=[
        cts.PRONOUNCIATION_EDGE_ID, '1soij3rlgbkct9eq3uo7117sa9', cts.ARE_EDGE_ID])
    # then
    assert reference_fields == {
        '1soij3rlgbkct9eq3uo7117sa9': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>modulated by: enzymes</li><li>completely unrelated '
                                      'animation: (media)</li>',
        '4s27e1mvsb5jqoiuaqmnlo8m71': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>requires: neurotransmitters<br><img '
                                      'src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic '
                                      'amines</li><li><img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: '
                                      'Serotonin</li>',
        '6iivm8tpoqj2c0euaabtput14l': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits '
                                      'up: Serotonin, dopamine, adrenaline, noradrenaline</li>'}


def test_get_smr_note_sort_fields(smr_world_4_tests):
    # when
    sort_fields = smr_world_4_tests.get_smr_note_sort_fields(
        edge_ids=[cts.ARE_EDGE_ID, cts.EDGE_WITH_MEDIA_XMIND_ID])
    # then
    assert sort_fields == {'6iivm8tpoqj2c0euaabtput14l': '|{|{{{|\x7f{', '7ite3obkfmbcasdf12asd123ga': '||{{{'}


def test_get_updated_child_smr_notes(smr_world_with_example_map):
    # when
    child_notes = smr_world_with_example_map.get_updated_child_smr_notes([cts.EXAMPLE_IMAGE_EDGE_ID])
    # then
    assert_that(list(child_notes)).contains(
        cts.EXAMPLE_IMAGE_EDGE_ID, cts.AFFECTS_EDGE_ID, cts.PRONOUNCIATION_EDGE_ID, cts.DIFFERENCE_EDGE_ID)


def test_generate_notes(smr_world_4_tests, collection_4_migration):
    # given
    cut = smr_world_4_tests
    # when
    notes = cut.generate_notes(col=collection_4_migration, edge_ids=[cts.ARE_EDGE_ID])
    # then
    imported_note = notes[cts.ARE_EDGE_ID]
    assert imported_note.fieldsStr == 'biological psychology<li>investigates: information transfer and ' \
                                      'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits ' \
                                      'up: Serotonin, dopamine, adrenaline, noradrenaline</li>arebiogenic ' \
                                      'amines|{|{{{|{'
    assert imported_note.tags == [' Example::test_file::test_sheet ', cts.ARE_EDGE_ID]


def test_get_xmind_sheets_in_file(smr_world_with_example_map):
    # when
    sheets = smr_world_with_example_map.get_xmind_sheets_in_file(file_directory=cts.DIRECTORY_MAPS_TEMPORARY,
                                                                 file_name=cts.NAME_EXAMPLE_MAP)
    # then
    assert [s.name for s in sheets.values()] == ['biological psychology', 'clinical psychology']


def test_get_note_ids_from_sheet_id(smr_world_with_example_map):
    # when
    notes_in_sheet = smr_world_with_example_map.get_note_ids_from_sheet_id(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert len(notes_in_sheet) == 21


def test_sort_id_from_order_number():
    # when
    sort_ids = [sort_id_from_order_number(i) for i in range(1, 21)]
    # then
    assert sort_ids == sorted(sort_ids)


def test_get_xmind_nodes_in_sheet(smr_world_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    nodes = cut.get_xmind_nodes_in_sheet(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert len(nodes) == 33
    assert nodes[cts.BIOGENIC_AMINES_2_NODE_ID]['parent_node_ids'] == set(cts.MULTIPLE_PARENTS_NODE_IDS)
    assert len(nodes[cts.NORADRENALINE_NODE_ID]['sibling_node_ids']) == 4


def test_get_root_node_id(smr_world_with_example_map):
    # when
    root_id = smr_world_with_example_map.get_root_node_id(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert root_id == cts.BIOLOGICAL_PSYCHOLOGY_NODE_ID


def test_get_xmind_edges_in_sheet(smr_world_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    edges = cut.get_xmind_edges_in_sheet(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert len(edges) == 25
    assert len(edges[cts.ARE_EDGE_ID]['parent_node_ids']) == 4
    assert len(edges[cts.AFFECTS_EDGE_ID]['child_node_ids']) == 3
    assert len(edges[cts.AFFECTS_EDGE_ID]['parent_node_ids']) == 1
    assert edges[cts.ARE_EDGE_ID]['xmind_edge'].content == cts.ARE_EDGE_CONTENT
    assert len(edges[cts.PRONOUNCIATION_EDGE_ID]['sibling_edge_ids']) == 3


def test_remove_xmind_sheets(smr_world_with_example_map, collection_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    cut.remove_xmind_sheets([cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID])
    # then
    assert cut.get_note_ids_from_sheet_id(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID) == set()
    assert cut.get_xmind_edges_in_sheet(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID) == {}
    assert cut.get_xmind_nodes_in_sheet(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID) == {}
    assert len(cut.get_xmind_sheets_in_file(cts.DIRECTORY_MAPS_TEMPORARY, cts.NAME_EXAMPLE_MAP)) == 1
    assert cut._get_records("select * from main.resources where iri like '%Pain'") == []
    assert not XOntology(collection_with_example_map.decks.id('testdeck', create=False),
                         cut).Serotonin.pronounciation_xrelation


def test_get_tag_by_sheet_id(smr_world_with_example_map, collection_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    tag = cut.get_tag_by_sheet_id(sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID,
                                  anki_collection=collection_with_example_map)
    # then
    assert tag == ' testdeck::example_map::biological_psychology '


def test_get_edge_parent_and_child_storids(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    cut = onto.world
    # when
    parent_storids, child_storids = cut.get_edge_parent_and_child_storids(cts.ARE_EDGE_ID)
    # then
    assert_that([onto.get(i) for i in parent_storids]).contains(
        onto.Serotonin, onto.dopamine, onto.adrenaline, onto.noradrenaline)
    assert onto.get(child_storids.pop()) == onto.biogenic_amines


def test_get_storid_triples_from_smr_triples(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    cut = onto.world
    # when
    storid_triple = cut.get_storid_triples_from_smr_triples(
        [SmrTripleDto(cts.SEROTONIN_1_NODE_ID, cts.AFFECTS_EDGE_ID, cts.SLEEP_NODE_ID)]).pop()
    # then

    assert onto.get(storid_triple[0]) == onto.Serotonin
    assert onto.get(storid_triple[1]) == onto.affects_xrelation
    assert onto.get(storid_triple[2]) == onto.Sleep


def test_get_storid_triples_surrounding_node(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    cut = onto.world
    # when
    storid_triples = cut.get_storid_triples_surrounding_node(cts.NOCICEPTORS_NODE_ID)
    # then
    assert_that([onto.get(t.parent_storid) for t in storid_triples]).contains(onto.nociceptors, onto.Pain)
    assert_that([onto.get(t.relation_storid) for t in storid_triples]).contains(
        onto.triggered_by_xrelation, onto.can_be_xrelation)
    assert_that([onto.get(t.child_storid) for t in storid_triples]).contains(onto.nociceptors, onto.chemical)


# TODO: Use views in triggers in smrworld.sql
def test_get_parent_node_ids_from_edge_id(smr_world_with_example_map):
    # given
    cut = smr_world_with_example_map
    # when
    parent_node_ids = cut.get_parent_node_ids_from_edge_id(cts.ARE_EDGE_ID)
    # then
    assert parent_node_ids == set(cts.MULTIPLE_PARENTS_NODE_IDS)


def test_remove_smr_triples_by_child_node_ids(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    cut = onto.world
    # when
    cut.remove_smr_triples_by_child_node_ids([(cts.NORADRENALINE_NODE_ID,)])
    onto.reload()
    # then
    assert_that(onto.MAO.splits_up_xrelation).does_not_contain(onto.noradrenaline)
