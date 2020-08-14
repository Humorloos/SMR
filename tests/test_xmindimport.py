import pickle

import pytest
from assertpy import assert_that
from bs4 import Tag

import tests.constants as cts
from smr.consts import X_MAX_ANSWERS, X_MODEL_NAME
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.template import add_x_model
from smr.xmanager import get_node_content, get_non_empty_sibling_nodes, get_parent_node
from smr.xmindimport import XmindImporter
from smr.xnotemanager import get_smr_note_reference_fields, get_smr_note_sort_fields


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
    assert [x.file for x in cut.x_managers] == expected_x_manager_files


def test_open_aborts_if_file_already_exists(xmind_importer, smr_world_4_tests):
    """
    Test whether the import stops when the file to be imported is already in the world
    """
    # given
    cut = xmind_importer
    cut.smr_world = smr_world_4_tests
    cut.file = cts.TEST_FILE_PATH
    # when
    cut.open()
    # then
    assert cut.log == [
        "It seems like {seed_path} is already in your collection. Please choose a different file.".format(
            seed_path=cts.TEST_FILE_PATH)]
    assert_that(cut.is_running).is_false()


def test_initialize_import(mocker, xmind_importer):
    # given
    cut = xmind_importer
    deck_name = 'my deck'
    mocker.patch.object(cut.col.decks, 'get', return_value={'name': deck_name})
    mocker.patch.object(cut, '_mw')
    mocker.patch.object(cut, "finish_import")
    mocker.patch('smr.xmindimport.XOntology')
    mocker.patch.object(cut, 'import_file')
    mocker.patch.object(cut, 'col')
    cut.model = {'id': 'my mid'}
    # when
    xmind_importer.initialize_import(DeckSelectionDialogUserInputsDTO())
    # then
    cut.mw.progress.start.assert_called_once()
    assert cut.import_file.call_count == 2


def test_import_file(xmind_importer, mocker, x_manager):
    # given
    cut = xmind_importer
    mocker.patch.object(cut, "import_sheet")
    mocker.patch.object(cut, "_mw")
    cut.deck_id = cts.TEST_DECK_ID
    # when
    cut.import_file(x_manager)
    # then
    assert cut.import_sheet.call_count == 2
    assert cut.files_2_import[0].directory == cts.RESOURCES_PATH
    assert cut.files_2_import[0].deck_id == cts.TEST_DECK_ID
    assert cut.files_2_import[0].file_name == cts.EXAMPLE_MAP_NAME


def test_import_sheet(xmind_importer, mocker, x_manager):
    # given
    sheet_2_import = 'biological psychology'
    cut = xmind_importer
    mocker.patch.object(cut, "_mw")
    mocker.patch.object(cut, "import_node_if_concept")
    mocker.patch.object(cut, "_onto")
    cut._active_manager = x_manager
    # when
    cut.import_sheet(sheet_2_import)
    # then
    assert cut.mw.progress.update.call_count == 1
    assert cut.mw.app.processEvents.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.current_sheet_import == sheet_2_import
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.sheets_2_import[0].sheet_id == '2485j5qgetfevlt00vhrn53961'
    assert cut.sheets_2_import[0].file_directory == cts.RESOURCES_PATH
    assert cut.sheets_2_import[0].file_name == cts.EXAMPLE_MAP_NAME


@pytest.fixture
def active_xmind_importer(xmind_importer):
    importer = xmind_importer
    importer._current_sheet_import = "biological psychology"
    importer._active_manager = importer.x_managers[0]
    return importer


@pytest.fixture
def xmind_importer_import_node_if_concept(mocker, active_xmind_importer):
    importer = active_xmind_importer
    mocker.patch.object(importer, "import_edge")
    mocker.patch.object(importer, "import_triple")
    mocker.patch.object(importer, "add_image_and_media_to_collection")
    yield importer


def test_import_node_if_concept_root(xmind_importer_import_node_if_concept, tag_for_tests, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    # when
    cut.import_node_if_concept(node=tag_for_tests, concepts=[x_ontology.Root(
        x_ontology.field_translator.class_from_content(get_node_content(tag_for_tests)))])
    # then
    assert cut.import_triple.call_count == 0
    assert cut.import_edge.call_count == 2
    assert cut.add_image_and_media_to_collection.call_count == 1
    assert len(cut.nodes_2_import) == 1


def test_import_node_if_concept_no_concept(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut._x_managers[0].get_tag_by_id(cts.EMPTY_NODE_TAG_ID)
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
    assert cut._smr_world.add_xmind_nodes.call_count == 0
    assert cut.import_edge.call_count == 1
    assert cut._smr_world.add_images_and_media_to_collection_and_self.call_count == 0


def test_import_node_if_concept_following_multiple_concepts(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut._x_managers[0].get_tag_by_id("3oqcv5qlqhn28u1opce5i27709")
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
    assert cut.import_edge.call_count == 1
    assert cut.add_image_and_media_to_collection.call_count == 1
    assert len(cut.nodes_2_import) == 1


@pytest.fixture
def xmind_importer_import_edge(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.patch.object(importer, "_onto")
    mocker.patch.object(importer, "_mw")
    mocker.patch.object(importer, "import_node_if_concept")
    mocker.patch.object(importer, "add_image_and_media_to_collection")
    mocker.patch.object(importer, "generate_notes")
    return importer


def test_import_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    # when
    cut.import_edge(order_number=1, edge=cut._active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.add_image_and_media_to_collection.call_count == 1
    assert len(cut.edges_2_import) == 1


def assert_import_edge_not_executed(cut):
    assert cut.onto.concept_from_node_content.call_count == 0
    assert cut.smr_world.add_xmind_edge.call_count == 0
    assert cut.import_node_if_concept.call_count == 0
    assert cut.is_running is False
    assert cut.generate_notes.call_count == 0
    assert cut.add_image_and_media_to_collection.call_count == 0


def test_import_edge_no_child_nodes(xmind_importer_import_edge, x_ontology, mocker):
    # given
    cut = xmind_importer_import_edge
    mocker.patch("smr.xmindimport.get_child_nodes", return_value=[])
    mocker.patch("smr.xmindimport.get_edge_coordinates_from_parent_node", return_value='coordinates')
    # when
    cut.import_edge(order_number=1, edge=cut._active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == [
        "Warning:\nA Question titled types (path coordinates) is missing answers. Please adjust your Concept Map and "
        "try again."]


def test_import_edge_too_many_child_nodes(xmind_importer_import_edge, x_ontology, mocker):
    # given
    cut = xmind_importer_import_edge
    mocker.patch("smr.xmindimport.get_child_nodes", return_value=[Tag(name='tag')] * (X_MAX_ANSWERS + 1))
    mocker.patch("smr.xmindimport.is_empty_node", return_value=False)
    # when
    cut.import_edge(order_number=1, edge=cut._active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == [
        "Warning:\nA Question titled \"types\" has more than 20 answers. Make sure every Question in your Map is "
        "followed by no more than 20 Answers and try again."]


def test_import_edge_preceding_multiple_concepts(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut._active_manager.get_tag_by_id(cts.EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID)
    parent_node = get_parent_node(edge)
    # when
    cut.import_edge(order_number=1, edge=edge, parent_node_ids=[parent_node['id']],
                    parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))])
    # then
    assert cut.onto.concept_from_node_content.call_count == 4
    assert cut.import_node_if_concept.call_count == 5
    assert cut.add_image_and_media_to_collection.call_count == 1
    assert len(cut.edges_2_import) == 1


def test_import_edge_empty_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut._active_manager.get_tag_by_id("668iln3nrlmk5ibhnf4lvbbnmo")
    parent_node = get_parent_node(edge)
    # when
    cut.import_edge(order_number=1, edge=edge, parent_node_ids=[parent_node['id']],
                    parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))])
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.add_image_and_media_to_collection.call_count == 0
    assert len(cut.edges_2_import) == 1


def test_generate_notes(active_xmind_importer, smr_world_4_tests, collection_4_migration):
    # given
    cut = active_xmind_importer
    cut.col = collection_4_migration
    cut._smr_world = smr_world_4_tests
    # when
    cut.edge_ids_2_make_notes_of = [cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID]
    cut.generate_notes()
    # then
    imported_note = cut.notes_2_import[cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID]
    assert imported_note.fieldsStr == 'biological psychology<li>investigates: information transfer and ' \
                                      'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits ' \
                                      'up: Serotonin, dopamine, adrenaline, noradrenaline</li>arebiogenic ' \
                                      'amines|{|{{{|{'
    assert imported_note.tags == [' Example::test_file::test_sheet ', cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID]


def test_finish_import(active_xmind_importer, smr_world_4_tests, mocker, collection_4_migration):
    # given
    cut = active_xmind_importer
    cut.smr_world = smr_world_4_tests
    add_x_model(cut.col)
    cut.model = cut.col.models.byName(X_MODEL_NAME)
    cut.deck_id = 1
    mocker.patch.object(cut, "import_notes_and_cards")
    cut.col = collection_4_migration
    cut.edge_ids_2_make_notes_of = [cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID, cts.PRONOUNCIATION_EDGE_XMIND_ID,
                                    cts.EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID, cts.EDGE_WITH_MEDIA_XMIND_ID]
    cut.generate_notes()
    # when
    cut.finish_import()
    # then
    assert cut.import_notes_and_cards.call_count == 1


def test_initialize_import_import_import_notes_to_correct_deck(
        mocker, set_up_empty_smr_world, empty_anki_collection_function, patch_aqt_mw_empty_smr_world):
    # given
    collection = empty_anki_collection_function
    add_x_model(collection)
    cut = XmindImporter(col=collection, file=cts.EXAMPLE_MAP_PATH)
    test_deck_id = cut.col.decks.id(name="test_deck")
    mocker.spy(cut, "import_edge")
    mocker.spy(cut, "import_node_if_concept")
    mocker.spy(cut, "import_sheet")
    mocker.spy(cut, "import_triple")
    mocker.spy(cut, "import_file")
    n_cards_example_map = 39
    # when
    cut.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=test_deck_id))
    cut.finish_import()
    # then
    assert cut.import_file.call_count == 2
    assert cut.import_sheet.call_count == 3
    assert cut.import_edge.call_count == 34
    assert cut.import_node_if_concept.call_count == 47
    assert cut.import_triple.call_count == 46
    assert len(cut.log) == 1
    assert len(cut.col.db.execute("select * from cards where did = ?", test_deck_id)) == n_cards_example_map
    assert cut.col.db.execute('select type from cards') == n_cards_example_map * [[0]]
    assert len(cut.smr_world.graph.execute('select distinct card_id from main.smr_triples').fetchall()) == 40


# noinspection PyPep8Naming
def test_newData(xmind_importer, smr_world_4_tests):
    # given
    next_note_id = 1
    foreign_note = pickle.loads(cts.EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE)
    importer = xmind_importer
    add_x_model(importer.col)
    importer.model = importer.col.models.byName(X_MODEL_NAME)
    importer.smr_world = smr_world_4_tests
    # fields used in newData() that are not initialized on object creation
    importer._fmap = importer.col.models.fieldMap(importer.model)
    importer._nextID = next_note_id
    importer._ids = []
    importer._cards = []
    # when
    data = importer.newData(foreign_note)
    # then
    assert importer.smr_notes_2_add[0].edge_id == cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID
    assert importer.smr_notes_2_add[0].note_id == next_note_id
    assert len(data) == 11


@pytest.fixture
def add_image_and_media_importer(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.spy(importer.col.media, "write_data")
    mocker.spy(importer.col.media, "add_file")

    yield importer


def validate_add_image_and_media(cut: XmindImporter, add_file_call_count: int):
    new_image = cut.media_2_anki_files_2_import[0].anki_file_name
    assert cut.col.media.have(new_image)
    assert new_image in cut.col.media.check().unused
    assert cut.col.media.write_data.call_count == 1
    assert cut.col.media.add_file.call_count == add_file_call_count


def test_add_image_and_media_to_collection(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media_to_collection(content=cts.NEUROTRANSMITTERS_NODE_CONTENT)
    # then
    validate_add_image_and_media(cut=cut, add_file_call_count=0)


def test_add_image_and_media_to_collection_with_media_attachment(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media_to_collection(content=cts.MEDIA_ATTACHMENT_NODE_CONTENT)
    # then
    validate_add_image_and_media(cut=cut, add_file_call_count=0)


def test_add_image_and_media_to_collection_with_media_hyperlink(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    # when
    cut.add_image_and_media_to_collection(content=cts.MEDIA_HYPERLINK_NODE_CONTENT)
    # then
    validate_add_image_and_media(cut=cut, add_file_call_count=1)
