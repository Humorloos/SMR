import pickle

import pytest
from assertpy import assert_that
from bs4 import Tag

import aqt
import tests.constants as cts
from smr.consts import X_MAX_ANSWERS, X_MODEL_NAME
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from smr.dto.xmindfiledto import XmindFileDto
from smr.template import add_x_model
from smr.xmindimport import XmindImporter
from smr.xmindtopic import XmindNode


@pytest.fixture(scope='function')
def xmind_importer_import_edge(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.patch.object(importer, "_onto")
    mocker.patch.object(importer, "_mw")
    mocker.patch.object(importer, "import_node_if_concept")
    return importer


@pytest.fixture
def active_xmind_importer(xmind_importer):
    importer = xmind_importer
    importer._current_sheet_import = "biological psychology"
    return importer


@pytest.fixture
def xmind_importer_4_integration(empty_anki_collection_function, mocker, patch_aqt_mw_empty_smr_world):
    collection = empty_anki_collection_function
    add_x_model(collection)
    cut = XmindImporter(col=collection, file=cts.PATH_EXAMPLE_MAP_DEFAULT)
    test_deck_id = cut.col.decks.id(name="test_deck")
    mocker.spy(cut, "import_edge")
    mocker.spy(cut, "import_node_if_concept")
    mocker.spy(cut, "_import_sheet")
    mocker.spy(cut, "import_triple")
    mocker.spy(cut, "_import_file")
    return cut, test_deck_id


@pytest.fixture
def xmind_importer_import_node_if_concept(mocker, active_xmind_importer):
    importer = active_xmind_importer
    mocker.patch.object(importer, "import_edge")
    mocker.patch.object(importer, "import_triple")
    yield importer


@pytest.fixture
def add_image_and_media_importer(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.spy(importer.col.media, "write_data")
    mocker.spy(importer.col.media, "add_file")
    yield importer


def assert_import_edge_not_executed(cut):
    assert cut.onto.concept_from_node_content.call_count == 0
    assert cut.smr_world.add_xmind_edge.call_count == 0
    assert cut.import_node_if_concept.call_count == 0
    assert cut.is_running is False
    assert len(cut.media_uris_2_add) == 0


def test_xmind_importer(xmind_importer):
    # when
    cut = xmind_importer
    # then
    assert cut.x_manager.file == cts.PATH_EXAMPLE_MAP_TEMPORARY


def test_open_aborts_if_file_already_exists(empty_anki_collection_session, mocker, smr_world_4_tests):
    """
    Test whether the import stops when the file to be imported is already in the world
    """
    # given
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_4_tests
    aqt.mw.return_value = aqt.mw
    cut = XmindImporter(col=empty_anki_collection_session, file=cts.TEST_FILE_PATH)
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
    mocker.patch.object(cut, '_import_file')
    mocker.patch.object(cut, 'col')
    cut.model = {'id': 'my mid'}
    # when
    xmind_importer.initialize_import(DeckSelectionDialogUserInputsDTO())
    # then
    cut.mw.progress.start.assert_called_once()
    assert cut._import_file.call_count == 1


def test_import_file(xmind_importer, mocker, x_manager):
    # given
    cut = xmind_importer
    mocker.patch.object(cut, "_import_sheet")
    mocker.patch.object(cut, "_mw")
    cut.deck_id = cts.TEST_DECK_ID
    # when
    cut._import_file()
    # then
    assert cut._import_sheet.call_count == 2
    assert cut.files_2_import[0].directory == cts.DIRECTORY_MAPS_TEMPORARY
    assert cut.files_2_import[0].deck_id == cts.TEST_DECK_ID
    assert cut.files_2_import[0].file_name == cts.NAME_EXAMPLE_MAP


def test__import_sheet(xmind_importer, mocker, x_manager):
    # given
    sheet_2_import = cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID
    cut = xmind_importer
    mocker.patch.object(cut, "_mw")
    mocker.patch.object(cut, "import_node_if_concept")
    mocker.patch.object(cut, "_onto")
    cut._active_manager = x_manager
    # when
    cut._import_sheet(sheet_2_import)
    # then
    assert cut.mw.progress.update.call_count == 1
    assert cut.mw.app.processEvents.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert cut.current_sheet_import == sheet_2_import
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.sheets_2_import[0].sheet_id == cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID
    assert cut.sheets_2_import[0].file_directory == cts.DIRECTORY_MAPS_TEMPORARY
    assert cut.sheets_2_import[0].file_name == cts.NAME_EXAMPLE_MAP


def test_import_node_if_concept_root(xmind_importer_import_node_if_concept, xmind_node, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    # when
    cut.import_node_if_concept(node=xmind_node, concepts=[x_ontology.Root(
        x_ontology.field_translator.class_from_content(xmind_node.content))])
    # then
    assert cut.import_triple.call_count == 0
    assert cut.import_edge.call_count == 2
    assert len(cut.media_uris_2_add) == 0
    assert len(cut.nodes_2_import) == 1


def test_import_node_if_concept_no_concept(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut.x_manager.get_node_by_id(cts.EMPTY_NODE_ID)
    concepts = [x_ontology.concept_from_node_content(t.content, node_id='some_id') for t in
                node.non_empty_sibling_nodes]
    parent_edge = node.parent_edge
    parent_node = parent_edge.parent_nodes[0]
    # when
    cut.import_node_if_concept(
        node=node, concepts=concepts,
        parent_concepts=[x_ontology.concept_from_node_content(parent_node.content, node_id='some_id')],
        parent_relationship_class_name=x_ontology.field_translator.class_from_content(parent_edge.content),
        order_number=5)
    # then
    assert cut.import_triple.call_count == 0
    assert cut._smr_world.add_or_replace_xmind_nodes.call_count == 0
    assert cut.import_edge.call_count == 1
    assert len(cut.media_uris_2_add) == 0


def test_import_node_if_concept_following_multiple_concepts(xmind_importer_import_node_if_concept, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    node = cut.x_manager.get_node_by_id(cts.BIOGENIC_AMINES_NODE_ID)
    concepts = [x_ontology.concept_from_node_content(node.content, node_id='some_id')]
    parent_edge = node.parent_edge
    parent_nodes = parent_edge.parent_nodes
    # when
    cut.import_node_if_concept(
        node=node, concepts=concepts,
        parent_concepts=[x_ontology.concept_from_node_content(n.content, node_id='some_id') for
                         n in parent_nodes],
        parent_relationship_class_name=x_ontology.field_translator.class_from_content(parent_edge.content),
        order_number=1)
    # then
    assert cut.import_triple.call_count == 4
    assert cut.import_edge.call_count == 1
    assert len(cut.nodes_2_import) == 1
    assert len(cut.media_uris_2_add) == 0


def test_import_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    # when
    cut.import_edge(order_number=1, edge=cut.x_manager.get_edge_by_id(cts.TYPES_EDGE_ID),
                    parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert len(cut.edges_2_import) == 1
    assert len(cut.media_uris_2_add) == 0


def test_import_edge_no_child_nodes(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.x_manager.get_edge_by_id(cts.TYPES_EDGE_ID)
    edge.child_nodes = []
    # when
    cut.import_edge(order_number=1, edge=edge, parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == ["""\
Warning:
A Question titled "types" (reference: biological psychology
investigates: information transfer and processing
requires: neurotransmitters (image)) is missing answers. Please adjust your Concept Map and try again."""]


def test_import_edge_too_many_child_nodes(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.x_manager.get_edge_by_id(cts.TYPES_EDGE_ID)
    edge.child_nodes = [XmindNode(None, '', '')] * (X_MAX_ANSWERS + 1)
    for n in edge.child_nodes:
        n.is_empty = False
    # when
    cut.import_edge(order_number=1, edge=edge, parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert_import_edge_not_executed(cut)
    assert cut.log == ["""\
Warning:
A Question titled "types" (reference: biological psychology
investigates: information transfer and processing
requires: neurotransmitters (image)) has more than 20 answers. Make sure every Question in your Map is followed by no \
more than 20 Answers and try again."""]


def test_import_edge_preceding_multiple_concepts(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.x_manager.get_edge_by_id(cts.SPLITS_UP_EDGE_ID)
    parent_node = edge.parent_nodes[0]
    # when
    cut.import_edge(order_number=1, edge=edge,
                    parent_concepts=[x_ontology.concept_from_node_content(parent_node.content, node_id='some_id')])
    # then
    assert cut.onto.concept_from_node_content.call_count == 4
    assert cut.import_node_if_concept.call_count == 5
    assert len(cut.edges_2_import) == 1
    assert len(cut.media_uris_2_add) == 0


def test_import_edge_empty_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.x_manager.get_edge_by_id(cts.EMPTY_EDGE_ID)
    parent_node = edge.parent_nodes[0]
    # when
    cut.import_edge(order_number=1, edge=edge,
                    parent_concepts=[x_ontology.concept_from_node_content(parent_node.content, node_id='some_id')])
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.import_node_if_concept.call_count == 1
    assert len(cut.edges_2_import) == 1
    assert len(cut.media_uris_2_add) == 0


def test_finish_import(patch_aqt_mw_smr_world_and_col_with_example_map, mocker):
    # given
    cut = XmindImporter(col=aqt.mw.col, file=cts.PATH_EXAMPLE_MAP_TEMPORARY)
    mocker.patch.object(cut, "import_notes_and_cards")
    cut.notes_2_import = cut.smr_world.generate_notes(col=cut.col, edge_ids=[
        cts.TYPES_EDGE_ID, cts.SPLITS_UP_EDGE_ID, cts.CONSIST_OF_EDGE_ID])
    # when
    cut.finish_import()
    # then
    assert cut.import_notes_and_cards.call_count == 1


def test_initialize_import_import_import_notes_to_correct_deck(xmind_importer_4_integration):
    # given
    cut, test_deck_id = xmind_importer_4_integration
    n_cards_example_map = 35
    # when
    cut.initialize_import(DeckSelectionDialogUserInputsDTO(deck_id=test_deck_id))
    cut.finish_import()
    # then
    assert cut._import_file.call_count == 1
    assert cut._import_sheet.call_count == 2
    assert cut.import_edge.call_count == 31
    assert cut.import_node_if_concept.call_count == 42
    assert cut.import_triple.call_count == 42
    assert len(cut.log) == 1
    assert len(cut.col.db.execute("select * from cards where did = ?", test_deck_id)) == n_cards_example_map
    assert cut.col.db.execute('select type from cards') == n_cards_example_map * [[0]]
    assert len(cut.smr_world.graph.execute('select distinct card_id from main.smr_triples').fetchall()) == 36


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
    assert importer.smr_notes_2_add[0].edge_id == cts.ARE_EDGE_ID
    assert importer.smr_notes_2_add[0].note_id == next_note_id
    assert len(data) == 11


def validate_add_image_and_media(cut: XmindImporter, add_file_call_count: int):
    new_image = cut.media_2_anki_files_2_import[0].anki_file_name
    assert cut.col.media.have(new_image)
    assert new_image in cut.col.media.check().unused
    assert cut.col.media.write_data.call_count == 1
    assert cut.col.media.add_file.call_count == add_file_call_count


def test__add_media_2_anki_collection(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    cut.media_uris_2_add.append(cts.NEUROTRANSMITTERS_IMAGE_ATTACHMENT_NAME)
    # when
    cut._add_media_2_anki_collection()
    # then
    validate_add_image_and_media(cut=cut, add_file_call_count=0)


def test__add_media_2_anki_collection_with_media_hyperlink(add_image_and_media_importer):
    # given
    cut = add_image_and_media_importer
    cut.media_uris_2_add.append(cts.PATH_HYPERLINK_MEDIA_TEMPORARY)
    # when
    cut._add_media_2_anki_collection()
    # then
    validate_add_image_and_media(cut=cut, add_file_call_count=1)


def test_import_sheet(xmind_importer_4_integration):
    # given
    cut, test_deck_id = xmind_importer_4_integration
    cut.files_2_import.append(
        XmindFileDto(directory=cts.DIRECTORY_MAPS_DEFAULT, file_name=cts.NAME_EXAMPLE_MAP, map_last_modified=5,
                     file_last_modified=5.0, deck_id=test_deck_id))
    # when
    cut.import_sheet(sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID, deck_id=test_deck_id)
    cut.finish_import()
    # then
    assert cut._import_sheet.call_count == 1
    assert cut.import_edge.call_count == 22
    assert cut.import_node_if_concept.call_count == 30
    assert cut.import_triple.call_count == 31
    assert len(cut.log) == 1
    assert len(cut.col.db.execute("select * from cards where did = ?", test_deck_id)) == 25
    assert cut.col.db.execute('select type from cards') == 25 * [[0]]
    assert len(cut.smr_world.graph.execute('select distinct card_id from main.smr_triples').fetchall()) == 26
