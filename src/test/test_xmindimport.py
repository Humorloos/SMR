import pytest
# class TestImportOntology(TestImportMap):
#     def setUp(self):
#         super().setUp()
#         importer = self.xmindImporter
#         importer.x_managers.append(
#             XManager(os.path.join(
#                 ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
#         importer.import_map()
#         importer.currentSheetImport = 'clinical psychology'
#         importer.import_map()
#         importer.activeManager = importer.x_managers[1]
#         importer.currentSheetImport = 'general psychology'
#         importer.import_map()
#
#     def test_example(self):
#         importer = self.xmindImporter
#         importer.import_ontology()
#         self.fail()
#
#
# class TestNoteFromQuestionList(TestImportOntology):
#     def test_multiple_answers(self):
#         importer = self.xmindImporter
#         questionList = [(315, 317, 318), (315, 317, 319)]
#         act = importer.note_from_question_list(questionList)
#         self.fail()
#
#     def test_bridge_parent(self):
#         importer = self.xmindImporter
#         questionList = [(328, 346, 325)]
#         act = importer.note_from_question_list(questionList)
#         self.fail()
#
#
# class TestGetXMindMeta(TestImportOntology):
#     def test_multiple_answers(self):
#         importer = self.xmindImporter
#         noteData = pickle.load(
#             open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'noteData.p'),
#                  'rb'))
#         act = importer.get_xmind_meta(noteData)
#         self.fail()
#
#
# class TestUpdateStatus(TestImportOntology):
#     def setUp(self):
#         super().setUp()
#         self.xmindImporter.import_ontology()
#
#     def test_update_status(self):
#         importer = self.xmindImporter
#         importer.update_status()
#         os.remove(importer.statusManager.status_file)
#         self.fail()
from bs4 import Tag

import test.constants as cts
from main.consts import X_MAX_ANSWERS
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.xmanager import get_node_content, get_non_empty_sibling_nodes, get_parent_node


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


def test_open_aborts_if_file_already_exists(mocker, xmind_importer, smr_world_for_tests):
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
    assert cut.mw.smr_world.add_xmind_file.call_count == 1


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
    assert cut.mw.smr_world.add_xmind_sheet.call_count == 1
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
    mocker.patch.object(importer, "mw")
    mocker.patch.object(importer, "import_edge")
    mocker.patch.object(importer, "import_triple")
    yield importer


def test_import_node_if_concept_root(xmind_importer_import_node_if_concept, tag_for_tests, x_ontology):
    # given
    cut = xmind_importer_import_node_if_concept
    # when
    cut.import_node_if_concept(node=tag_for_tests, concepts=[x_ontology.Root(
        x_ontology.field_translator.class_from_content(get_node_content(tag_for_tests)))])
    # then
    assert cut.import_triple.call_count == 0
    assert cut.mw.smr_world.add_xmind_node.call_count == 1
    assert cut.import_edge.call_count == 2


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
    assert cut.mw.smr_world.add_xmind_node.call_count == 0
    assert cut.import_edge.call_count == 1


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
    assert cut.mw.smr_world.add_xmind_node.call_count == 1
    assert cut.import_edge.call_count == 0


@pytest.fixture
def xmind_importer_import_edge(active_xmind_importer, mocker):
    # given
    importer = active_xmind_importer
    mocker.patch.object(importer, "onto")
    mocker.patch.object(importer, "mw")
    mocker.patch.object(importer, "import_node_if_concept")
    return importer


def test_import_edge(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    # when
    cut.import_edge(order_number=1, edge=cut.active_manager.get_tag_by_id(cts.TYPES_EDGE_XMIND_ID), parent_node_ids=[
        cts.NEUROTRANSMITTERS_XMIND_ID], parent_concepts=x_ontology.Concept(cts.NEUROTRANSMITTERS_CLASS_NAME))
    # then
    assert cut.onto.concept_from_node_content.call_count == 1
    assert cut.mw.smr_world.add_xmind_edge.call_count == 1
    assert cut.import_node_if_concept.call_count == 1


def assert_import_edge_not_executed(cut):
    assert cut.onto.concept_from_node_content.call_count == 0
    assert cut.mw.smr_world.add_xmind_edge.call_count == 0
    assert cut.import_node_if_concept.call_count == 0
    assert cut.running is False


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


def test_import_edge_following_multiple_concepts(xmind_importer_import_edge, x_ontology):
    # given
    cut = xmind_importer_import_edge
    edge = cut.active_manager.get_tag_by_id("61irckf1nloq42brfmbu0ke92v")
    parent_node = get_parent_node(edge)
    # when
    cut.import_edge(order_number=1, edge=edge, parent_node_ids=[parent_node['id']],
                    parent_concepts=[x_ontology.concept_from_node_content(get_node_content(parent_node))])
    # then
    assert cut.onto.concept_from_node_content.call_count == 4
    assert cut.mw.smr_world.add_xmind_edge.call_count == 1
    assert cut.import_node_if_concept.call_count == 5
