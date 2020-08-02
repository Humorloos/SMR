import pickle

import pytest
from bs4 import Tag

import aqt
import test.constants as cts
from main.consts import X_MAX_ANSWERS, X_MODEL_NAME
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.template import add_x_model
from main.xmanager import get_node_content, get_non_empty_sibling_nodes, get_parent_node
from main.xmindimport import XmindImporter


def test_xmind_importer(xmind_importer):
    # given
    expected_x_manager_files = [
        'C:\\Users\\lloos\\OneDrive - bwedu\\Projects\\AnkiAddon\\anki-addon-dev\\addons21\\XmindImport\\resources'
        '\\example map.xmind',
        'C:\\Users\\lloos\\OneDrive - bwedu\\Projects\\AnkiAddon\\anki-addon-dev\\addons21\\XmindImport\\resources'
        '\\example_general_psychology.xmind']
    # when
    cut = xmind_importer
    # then
    assert [x.get_file() for x in cut.x_managers] == expected_x_manager_files


def test_open_aborts_if_file_already_exists(mocker, xmind_importer):
    """
    Test whether the import stops when the file to be imported is already in the world
    """
    # given
    cut = xmind_importer
    mocker.patch.object(cut, "mw")
    # when
    cut.open()
    # then
    assert cut.log == [
        "It seems like {seed_path} is already in your collection. Please choose a different file.".format(
            seed_path=cts.EXAMPLE_MAP_PATH)]


def test_initialize_import(mocker, xmind_importer):
    # given
    cut = xmind_importer
    deck_name = 'my deck'
    mocker.patch.object(cut.col.decks, 'get', return_value={'name': deck_name})
    mocker.patch.object(cut, 'mw')
    mocker.patch.object(cut, "finish_import")
    mocker.patch('main.xmindimport.XOntology')
    mocker.patch.object(cut, 'import_file')
    mocker.patch.object(cut, 'col')
    cut.col.models.byName.return_value = {'id': 'my mid'}
    # when
    xmind_importer.initialize_import(DeckSelectionDialogUserInputsDTO())
    # then
    cut.mw.progress.start.assert_called_once()
    cut.finish_import.assert_called_once()
    assert cut.import_file.call_count == 2
    assert cut.col.decks.select.call_count == 1
    assert cut.col.decks.current.call_count == 1


def test_import_file(xmind_importer, mocker, x_manager):
    # given
    cut = xmind_importer
    mocker.patch.object(cut, "import_sheet")
    mocker.patch.object(cut, "mw")
    # when
    cut.import_file(x_manager)
    # then
    assert cut.import_sheet.call_count == 2
    assert cut.smr_world.add_xmind_file.call_count == 1


def test_import_sheet(xmind_importer, mocker, x_manager):
    # given
    sheet_2_import = 'biological psychology'
    cut = xmind_importer
    mocker.patch.object(cut, "mw")
    mocker.patch.object(cut, "import_node_if_concept")
    mocker.patch.object(cut, "onto")
    cut.active_manager = x_manager
    # when
    cut.import_sheet(sheet_2_import)
    # then
    assert cut.mw.progress.update.call_count == 1
    assert cut.mw.app.processEvents.call_count == 1
    assert cut.smr_world.add_xmind_sheet.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.current_sheet_import == sheet_2_import
    assert cut.onto.concept_from_node_content.call_count == 1


@pytest.fixture
def active_xmind_importer(xmind_importer):
    importer = xmind_importer
    importer.current_sheet_import = "biological psychology"
    importer.active_manager = importer.x_managers[0]
    return importer


@pytest.fixture
def xmind_importer_import_node_if_concept(mocker, active_xmind_importer):
    importer = active_xmind_importer
    mocker.patch.object(importer, "import_edge")
    mocker.patch.object(importer, "import_triple")
    mocker.patch.object(importer, "add_image_and_media")

    yield importer


def test_import_node_if_concept_root(xmind_importer_import_node_if_concept, tag_for_tests, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    # when
    cut.import_node_if_concept(node=tag_for_tests, concepts=[x_ontology.Root(
        x_ontology.field_translator.class_from_content(get_node_content(tag_for_tests)))])
    # then
    assert cut.import_triple.call_count == 0
    assert cut.smr_world.add_xmind_node.call_count == 1
    assert cut.import_edge.call_count == 2
    assert cut.add_image_and_media.call_count == 1


def test_import_node_if_concept_no_concept(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut.x_managers[0].get_tag_by_id(cts.EMPTY_NODE_TAG_ID)
    concepts = [x_ontology.concept_from_node_content(get_node_content(t)) for t in
                get_non_empty_sibling_nodes(node)]
    parent_edge = get_parent_node(node)
    parent_node = get_parent_node(parent_edge)
    # when
    cut.import_node_if_concept(
        node=node, concepts=concepts, parent_node_ids=[parent_node['id']],
        parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))],
        parent_edge_id=parent_edge['id'],
        parent_relationship_class_name=x_ontology.field_translator.class_from_content(get_node_content(parent_edge)),
        order_number=5)
    # then
    assert cut.import_triple.call_count == 0
    assert cut.smr_world.add_xmind_node.call_count == 0
    assert cut.import_edge.call_count == 1
    assert cut.add_image_and_media.call_count == 0


def test_import_node_if_concept_following_multiple_concepts(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut.x_managers[0].get_tag_by_id("3oqcv5qlqhn28u1opce5i27709")
    concepts = [x_ontology.concept_from_node_content(get_node_content(node))]
    parent_edge = get_parent_node(node)
    parent_nodes = get_non_empty_sibling_nodes(get_parent_node(parent_edge))
    # when
    cut.import_node_if_concept(
        node=node, concepts=concepts, parent_node_ids=[n['id'] for n in parent_nodes],
        parent_concepts=[x_ontology.concept_from_node_content(get_node_content(n)) for n in parent_nodes],
        parent_edge_id=parent_edge['id'],
        parent_relationship_class_name=x_ontology.field_translator.class_from_content(get_node_content(parent_edge)),
        order_number=1)
    # then
    assert cut.import_triple.call_count == 4
    assert cut.smr_world.add_xmind_node.call_count == 1
    assert cut.import_edge.call_count == 0
    assert cut.add_image_and_media.call_count == 1


@pytest.fixture
def xmind_importer_import_edge(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.patch.object(importer, "onto")
    mocker.patch.object(importer, "mw")
    mocker.patch.object(importer, "import_node_if_concept")
    mocker.patch.object(importer, "add_image_and_media")
    mocker.patch.object(importer, "create_and_add_note")
    return importer


def test_import_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    # when
    cut.import_edge(order_number=1, edge=cut.active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.smr_world.add_xmind_edge.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.add_image_and_media.call_count == 1
    assert cut.create_and_add_note.call_count == 1


def assert_import_edge_not_executed(cut):
    assert cut.onto.concept_from_node_content.call_count == 0
    assert cut.smr_world.add_xmind_edge.call_count == 0
    assert cut.import_node_if_concept.call_count == 0
    assert cut.running is False
    assert cut.add_image_and_media.call_count == 0
    assert cut.create_and_add_note.call_count == 0


def test_import_edge_no_child_nodes(xmind_importer_import_edge, x_ontology, mocker):
    # given
    cut = xmind_importer_import_edge
    mocker.patch("main.xmindimport.get_child_nodes", return_value=[])
    mocker.patch("main.xmindimport.get_edge_coordinates_from_parent_node", return_value='coordinates')
    # when
    cut.import_edge(order_number=1, edge=cut.active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == [
        "Warning:\nA Question titled types (path coordinates) is missing answers. Please adjust your Concept Map and "
        "try again."]


def test_import_edge_too_many_child_nodes(xmind_importer_import_edge, x_ontology, mocker):
    # given
    cut = xmind_importer_import_edge
    mocker.patch("main.xmindimport.get_child_nodes", return_value=[Tag(name='tag')] * (X_MAX_ANSWERS + 1))
    mocker.patch("main.xmindimport.is_empty_node", return_value=False)
    # when
    cut.import_edge(order_number=1, edge=cut.active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == [
        "Warning:\nA Question titled \"types\" has more than 20 answers. Make sure every Question in your Map is "
        "followed by no more than 20 Answers and try again."]


def test_import_edge_preceding_multiple_concepts(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.active_manager.get_tag_by_id(cts.EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID)
    parent_node = get_parent_node(edge)
    # when
    cut.import_edge(order_number=1, edge=edge, parent_node_ids=[parent_node['id']],
                    parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))])
    # then
    assert cut.onto.concept_from_node_content.call_count == 4
    assert cut.smr_world.add_xmind_edge.call_count == 1
    assert cut.import_node_if_concept.call_count == 5
    assert cut.add_image_and_media.call_count == 1
    assert cut.create_and_add_note.call_count == 1


def test_import_edge_empty_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.active_manager.get_tag_by_id("668iln3nrlmk5ibhnf4lvbbnmo")
    parent_node = get_parent_node(edge)
    # when
    cut.import_edge(order_number=1, edge=edge, parent_node_ids=[parent_node['id']],
                    parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))])
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.smr_world.add_xmind_edge.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.add_image_and_media.call_count == 0
    assert cut.create_and_add_note.call_count == 0


@pytest.fixture
def add_image_and_media_importer(mocker, active_xmind_importer):
    importer = active_xmind_importer
    mocker.spy(importer.col.media, 'write_data')
    mocker.spy(importer.col.media, 'add_file')
    mocker.patch.object(importer, 'mw')
    yield importer


# noinspection DuplicatedCode
def test_add_image_and_media(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media(cts.NEUROTRANSMITTERS_NODE_CONTENT)
    # then
    new_image = cut.smr_world.add_xmind_media_to_anki_file.call_args[1]['anki_file_name']
    assert cut.col.media.have(new_image)
    assert new_image in cut.col.media.check().unused
    assert cut.col.media.write_data.call_count == 1
    assert cut.col.media.add_file.call_count == 0


# noinspection DuplicatedCode
def test_add_image_and_media_with_media_attachment(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media(cts.MEDIA_ATTACHMENT_NODE_CONTENT)
    # then
    new_media = cut.smr_world.add_xmind_media_to_anki_file.call_args[1]['anki_file_name']
    assert cut.col.media.have(new_media)
    assert new_media in cut.col.media.check().unused
    assert cut.col.media.write_data.call_count == 1
    assert cut.col.media.add_file.call_count == 0


# noinspection DuplicatedCode
def test_add_image_and_media_with_media_hyperlink(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media(cts.MEDIA_HYPERLINK_NODE_CONTENT)
    # then
    new_media = cut.smr_world.add_xmind_media_to_anki_file.call_args[1]['anki_file_name']
    assert cut.col.media.have(new_media)
    assert new_media in cut.col.media.check().unused
    assert cut.col.media.write_data.call_count == 1
    assert cut.col.media.add_file.call_count == 1


def test_create_and_add_note(mocker, active_xmind_importer, smr_world_for_tests):
    # given
    cut = active_xmind_importer
    cut.smr_world = smr_world_for_tests
    mocker.spy(cut, "acquire_tag")
    # when
    cut.create_and_add_note(edge_id=cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert cut.acquire_tag.call_count == 1
    assert pickle.dumps(cut._notes_2_import[0]) == cts.EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE


def test_acquire_tag(active_xmind_importer):
    # given
    cut = active_xmind_importer
    cut.deck_name = 'my deck'
    # when
    tag = cut.acquire_tag()
    # then
    assert tag == 'my_deck::biological_psychology'


def test_finish_import(active_xmind_importer, smr_world_for_tests, mocker):
    # given
    cut = active_xmind_importer
    cut.smr_world = smr_world_for_tests
    add_x_model(cut.col)
    cut.model = cut.col.models.byName(X_MODEL_NAME)
    cut.deck_id = 1
    mocker.patch.object(cut.smr_world, "add_smr_note")
    mocker.patch.object(cut.smr_world, "update_smr_triples_card_id")
    mocker.patch.object(cut.smr_world, "save")
    for edge_id in [cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID, cts.PRONOUNCIATION_EDGE_XMIND_ID,
                    cts.EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID, cts.EDGE_WITH_MEDIA_XMIND_ID]:
        cut.create_and_add_note(edge_id)
    # when
    cut.finish_import()
    # then
    assert cut.smr_world.add_smr_note.call_count == 4
    assert cut.smr_world.update_smr_triples_card_id.call_count == 7
    assert cut.smr_world.save.call_count == 1


def test_initialize_import_import_import_notes_to_correct_deck(mocker, empty_smr_world, empty_anki_collection_function):
    # given
    mocker.patch("aqt.mw")
    aqt.mw.smr_world = empty_smr_world
    collection = empty_anki_collection_function
    add_x_model(collection)
    cut = XmindImporter(col=collection, file=cts.EXAMPLE_MAP_PATH)
    cut.smr_world.set_up()
    test_deck_id = cut.col.decks.id(name="test_deck")
    mocker.spy(cut, "import_edge")
    mocker.spy(cut, "import_node_if_concept")
    mocker.spy(cut, "import_sheet")
    mocker.spy(cut, "import_triple")
    mocker.spy(cut, "import_file")
    # when
    cut.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=test_deck_id))
    # then
    assert cut.import_file.call_count == 2
    assert cut.import_sheet.call_count == 3
    assert cut.import_edge.call_count == 32
    assert cut.import_node_if_concept.call_count == 45
    assert cut.import_triple.call_count == 44
    assert len(cut.log) == 1
    assert len(cut.col.db.execute("select * from cards where did = ?", test_deck_id)) == 37
    assert cut.col.db.execute('select type from cards') == 37 * [[0]]


# noinspection PyPep8Naming
def test_newData(xmind_importer, smr_world_for_tests):
    # given
    next_note_id = 1
    foreign_note = pickle.loads(cts.EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE)
    importer = xmind_importer
    add_x_model(importer.col)
    importer.model = importer.col.models.byName(X_MODEL_NAME)
    importer._fmap = importer.col.models.fieldMap(importer.model)
    importer._nextID = next_note_id
    importer._ids = []
    importer._cards = []
    importer.smr_world = smr_world_for_tests
    # when
    importer.newData(foreign_note)
    # then
    assert importer.smr_world.graph.execute("SELECT * FROM smr_notes").fetchone()[:2] == (
        next_note_id, cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
