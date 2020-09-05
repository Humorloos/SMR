import os

import pytest
from assertpy import assert_that

import aqt
import tests.constants as cts
from anki import Collection
from conftest import generate_new_file
import smr.smrsynchronizer
from smr.dto.topiccontentdto import TopicContentDto
from smr.fieldtranslator import CHILD_RELATION_NAME, relation_class_from_content, class_from_content
from smr.smrsynchronizer import SmrSynchronizer
from smr.smrworld import SmrWorld
from smr.xmanager import XManager
from smr.xnotemanager import XNoteManager, field_from_content


@pytest.fixture
def smr_synchronizer_no_changes(patch_aqt_mw_smr_world_and_col_with_example_map):
    generate_default_example_map()
    return SmrSynchronizer()


@pytest.fixture
def smr_synchronizer_local_changes(patch_aqt_mw_smr_world_and_changed_col_with_example_map):
    generate_default_example_map()
    yield SmrSynchronizer()


def generate_default_example_map():
    generate_new_file(src=cts.PATH_EXAMPLE_MAP_DEFAULT, dst=cts.PATH_EXAMPLE_MAP_TEMPORARY)
    generate_new_file(src=cts.PATH_MAP_GENERAL_PSYCHOLOGY_DEFAULT, dst=cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY)


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
    mocker.spy(cut, '_process_remote_file_changes')
    mocker.spy(cut, 'process_local_and_remote_changes')
    # when
    cut.synchronize()
    # then
    assert cut._process_local_changes.call_count == 0
    assert cut._process_remote_file_changes.call_count == 0
    assert cut.process_local_and_remote_changes.call_count == 0


def test_synchronize_local_changes(smr_synchronizer_local_changes, mocker, changed_collection_with_example_map):
    # given
    cut = smr_synchronizer_local_changes
    mocker.spy(cut, '_process_local_changes')
    mocker.spy(cut, '_process_remote_file_changes')
    mocker.spy(cut, 'process_local_and_remote_changes')
    # when
    cut.synchronize()
    # then
    x_manager = XManager(cts.PATH_EXAMPLE_MAP_TEMPORARY)
    assert x_manager.get_node_content_by_id(cts.ENZYMES_NODE_ID) == TopicContentDto(
        image=cts.NEW_IMAGE_NAME, title='enzymes')
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
    assert cut.onto.biogenic_amines.former_image_xrelation == [cut.onto.Serotonin_new]
    assert cut.onto.Serotonin_new.pronounciation_xrelation == [cut.onto.get_concept_from_node_id(
        cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)]
    assert getattr(cut.onto.Serotonin_new, CHILD_RELATION_NAME) == [cut.onto.get_concept_from_node_id(
        cts.MAO_1_NODE_ID)]
    assert len(cut.smr_world._get_records("SELECT * from main.xmind_nodes where title = 'Serotonin new'")) == 1
    print(cut.log)
    assert f'Cannot add media "{cts.NEW_MEDIA_NAME}"' in cut.log[0]
    assert cut.col.getNote(cut.col.findNotes('in english')[0]).fields[2] == 'virtue'
    assert getattr(cut.onto, class_from_content(TopicContentDto(
        media=cts.DE_ATTACHMENT_NAME))).means_in_english_xrelation[0] == cut.onto.virtue
    assert x_manager.get_edge_by_id(cts.EXAMPLE_IMAGE_EDGE_ID).content == TopicContentDto(title='former image')


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


def test_synchronize_remote_changes(mocker, smr_world_with_example_map, collection_with_example_map):
    # given
    generate_new_file(cts.PATH_EXAMPLE_MAP_CHANGED, cts.PATH_EXAMPLE_MAP_TEMPORARY)
    generate_new_file(cts.PATH_MAP_GENERAL_PSYCHOLOGY_CHANGED, cts.PATH_MAP_GENERAL_PSYCHOLOGY_TEMPORARY)
    generate_new_file(cts.PATH_HYPERLINK_MEDIA_CHANGED, cts.PATH_HYPERLINK_MEDIA_TEMPORARY)
    generate_new_file(cts.PATH_MAP_NEW_PSYCHOLOGY, os.path.join(
        cts.DIRECTORY_MAPS_TEMPORARY, cts.NAME_NEW_PSYCHOLOGY + '.xmind'))
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_with_example_map
    aqt.mw.col = collection_with_example_map
    aqt.mw.return_value = aqt.mw
    cut = smr.smrsynchronizer.SmrSynchronizer()
    # when
    cut.synchronize()
    # then
    assert_that(cut.onto.information_transfer_and_processing.new_question_xrelation).contains(
        cut.onto.answer_1, cut.onto.answer_2)
    assert_that([n['xmind_node'].title for n in cut.smr_world.get_xmind_nodes_in_sheet(
        cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID).values()]).contains('answer 1', 'answer 2', 'answer 2.1', 'answer 3.1')
    assert_that([r.name for r in cut.smr_world._get_records('select * from main.xmind_sheets')]).contains(
        'biological psychology', 'general psychology', 'New sheet')
    assert_that(cut.col.tags.all()).contains_only(
        'testdeck::example_general_psychology::general_psychology', 'testdeck::example_map::biological_psychology',
        'testdeck::example_map::New_sheet')
    assert len(cut.col.findNotes('New_Sheet')) == 3
    assert_that([r['xmind_node'].title for r in cut.smr_world.get_xmind_nodes_in_sheet(
        cts.NEW_SHEET_SHEET_ID).values()]).contains(
        'New sheet', 'first new sheet topic', 'another one', 'yet another one', 'answer to this other question',
        'yet another answer')
    assert cut.onto.another_one.question_following_these_multiple_answers_xrelation == [cut.onto.yet_another_answer]
    assert_that([c.new_question_following_multiple_answers_xrelation for c in [
        cut.onto.Margret, cut.onto.new_answer]]).is_length(2).contains_only([cut.onto.answer_following_mult_answers])
    assert cut.onto.enzymes.example_xrelation == []
    assert cut.col.findNotes('enzymes example') == []
    assert cut.onto.neurotransmitters_changed_textximage_629d18n2i73im903jkrjmr98fg_extension_png.types_xrelation == [
        cut.onto.biogenic_amines, cut.onto.enzymes]
    former_image_title = 'example (former image)'
    assert set(cut.col.getNote(n).fields[1] for n in cut.col.findNotes('neurotransmitters changed text')) == {
        'pronounciation', 'completely unrelated animation', 'affects', 'types', former_image_title,
        'difference to MAO', 'requires', 'new question following multiple answers all there', 'mult bridge question',
        'question to new bridge answer'}
    assert cut.smr_world.get_smr_note_reference_fields([cts.EXAMPLE_IMAGE_EDGE_ID])[cts.EXAMPLE_IMAGE_EDGE_ID][
           :196] == cut.smr_world.get_smr_note_reference_fields([cts.COMPLETELY_UNRELATED_ANIMATION_EDGE_ID])[
                        cts.COMPLETELY_UNRELATED_ANIMATION_EDGE_ID][:196]
    assert cut.smr_world._get_records(
        "select order_number from main.xmind_nodes where title = 'psychological disorders'")[0][0] == 1
    assert cut.col.getNote(cut.col.findNotes('affects')[0]).fields[2] == 'psychological disorders'
    assert getattr(cut.onto.biogenic_amines, relation_class_from_content(
        TopicContentDto(title=former_image_title)))[0] == cut.onto.Serotonin
    assert len(cut.col.findNotes(former_image_title)) > 0
    assert_that([n['xmind_edge'].content for n in cut.smr_world.get_xmind_edges_in_sheet(
        cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID).values()]).contains(
        TopicContentDto(title=former_image_title),
        TopicContentDto(image='attachments/3rqffo150j4thev5vlag2sgcu6.png', title='can be inhibited by'))
    assert cut.onto.Pain.can_be_inhibited_byximage_3rqffo150j4thev5vlag2sgcu6_extension_png_xrelation[
               0] == cut.onto.Serotonin
    assert cut.col.getNote(cut.col.findNotes('can be inhibited by')[0]).fields[
               1] == 'can be inhibited by<br><img src="attachments3rqffo150j4thev5vlag2sgcu6.png">'

# TODO: also add an image to an answer in the map and add a test for this
# TODO: add test case for added media for remote sync for both answers and questions (can be the 环境很好 file)
# TODO: add file selection dialog if file was not found
# TODO: add log entries for changes made
# TODO: show log after sync
