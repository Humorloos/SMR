import pytest

import aqt
import tests.constants as cts
from anki import Collection
from conftest import generate_new_file
from smr.dto.nodecontentdto import NodeContentDto
from smr.smrsynchronizer import SmrSynchronizer
from smr.smrworld import SmrWorld
from smr.xmanager import XManager
from smr.xnotemanager import XNoteManager


@pytest.fixture
def smr_synchronizer_no_changes(patch_aqt_mw_smr_world_and_col_with_example_map):
    return SmrSynchronizer()


@pytest.fixture
def smr_synchronizer_local_changes(patch_aqt_mw_smr_world_and_changed_col_with_example_map):
    generate_new_file(src=cts.PATH_EXAMPLE_MAP_DEFAULT, dst=cts.PATH_EXAMPLE_MAP_TEMPORARY)
    generate_new_file(src=cts.PATH_MAP_GENERAL_PSYCHOLOGY_DEFAULT, dst=cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY)
    yield SmrSynchronizer()


def test_smr_synchronizer(smr_synchronizer_no_changes):
    # when
    cut = smr_synchronizer_no_changes
    # then
    assert type(cut.smr_world) == SmrWorld
    assert type(cut.note_manager) == XNoteManager
    assert type(cut.col) == Collection


def test_synchronize_no_changes(smr_synchronizer_no_changes, mocker):
    # given
    cut = smr_synchronizer_no_changes
    mocker.spy(cut, '_process_local_changes')
    mocker.spy(cut, '_process_remote_changes')
    mocker.spy(cut, 'process_local_and_remote_changes')
    # when
    cut.synchronize()
    # then
    assert cut._process_local_changes.call_count == 0
    assert cut._process_remote_changes.call_count == 0
    assert cut.process_local_and_remote_changes.call_count == 0


def test_synchronize_local_changes(smr_synchronizer_local_changes, mocker, changed_collection_with_example_map):
    # given
    cut = smr_synchronizer_local_changes
    mocker.spy(cut, '_process_local_changes')
    mocker.spy(cut, '_process_remote_changes')
    mocker.spy(cut, 'process_local_and_remote_changes')
    # when
    cut.synchronize()
    # then
    assert XManager(cts.PATH_EXAMPLE_MAP_TEMPORARY).get_node_content_by_id(cts.ENZYMES_NODE_ID) == NodeContentDto(
        image='paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg', title='enzymes')
    assert changed_collection_with_example_map.db.first(
        "select flds from notes where tags = ' testdeck::example_map::biological_psychology ' "
        "and sfld = '|{|{{{|~{'") == [
               'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: '
               'enzymes<br><img src="paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg"></li><li>example: '
               'MAO</li><li>splits up: Serotonin, dopamine, adrenaline</li>\x1fare changed question\x1fbiogenic '
               'amines\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f|{|{{{|~{']
    assert changed_collection_with_example_map.db.first(
        "select flds from notes where tags = ' testdeck::example_map::biological_psychology ' "
        "and sfld = '|{|{{{|~{{{'") == [
               'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: '
               'enzymes<br><img src="paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg"></li><li>example: '
               'MAO</li><li>splits up: Serotonin, dopamine, adrenaline</li><li>are changed question: biogenic '
               'amines</li>\x1fconsist of\x1fone or more amine '
               'groups\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f|{|{{{|~{{{']


def test_synchronize_answer_added_error(mocker, smr_world_with_example_map):
    # given
    generate_new_file(src=cts.DEFAULT_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_PATH,
                      dst=cts.TEMPORARY_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_with_example_map
    collection = Collection(cts.TEMPORARY_NEW_ANSWER_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    aqt.mw.col = collection
    aqt.mw.return_value = aqt.mw
    cut = SmrSynchronizer()
    # when
    cut.synchronize()
    # then
    assert cut.log == ['Invalid added answer: Cannot add answer "added answer" to question "are" (reference: '
                       'biological psychology<li>investigates: information transfer and processing</li><li>modulated '
                       'by: enzymes</li><li>example: MAO</li><li>splits up: Serotonin, dopamine, adrenaline, '
                       'noradrenaline</li>). Adding answers via anki is not yet supported, instead, add the answer in '
                       'your xmind map and synchronize. I removed the answer from the note.']
    assert collection.db.first(
        "select flds from notes where tags = ' testdeck::example_map::biological_psychology ' "
        "and sfld = '|{|{{{|{'") == [
               'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: '
               'enzymes</li><li>example: MAO</li><li>splits up: Serotonin, dopamine, adrenaline, '
               'noradrenaline</li>arebiogenic amines|{|{{{|{']


def test_synchronize_center_node_removed_error(mocker, smr_world_with_example_map):
    # given
    generate_new_file(src=cts.DEFAULT_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_PATH,
                      dst=cts.TEMPORARY_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_with_example_map
    collection = Collection(cts.TEMPORARY_REMOVED_CENTER_NODE_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    aqt.mw.col = collection
    aqt.mw.return_value = aqt.mw
    cut = SmrSynchronizer()
    # when
    cut.synchronize()
    # then
    assert cut.log == ['Invalid answer removal: Cannot remove answer "perception" to question "investigates" ('
                       'reference: biological psychology), because more questions follow this answer in the xmind '
                       'map. I restored the answer. If you want to remove the answer, do it in the concept map and '
                       'then synchronize.']
    assert collection.db.first(
        "select flds from notes where tags = ' testdeck::example_map::biological_psychology ' "
        "and sfld = '|'") == [
               'biological psychology\x1finvestigates\x1finformation transfer and '
               'processing\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f|']
