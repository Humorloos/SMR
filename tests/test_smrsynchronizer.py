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
from smr.xnotemanager import XNoteManager, field_from_content, get_field_by_identifier


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
    # All nodes and edges in the smr world must be mapped to a concept or relation in the ontology
    # Anki collection changes:
    assert cut.smr_world._get_records("""select storid from main.xmind_nodes where storid is null 
        union select storid from main.xmind_edges where storid is null""") == []


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
    former_image_title = 'example (former image)'

    def get_fields_by_question(question):
        return cut.col.getNote(cut.col.findNotes(f'Question:"{question}"')[0]).fields

    # Ontology changes:
    # Edge in ontology must reflect changed content of edge in map
    assert_that(cut.onto.information_transfer_and_processing.new_question_xrelation).contains(
        cut.onto.answer_1, cut.onto.answer_2)
    # Edge in ontology must reflect edge with added image and node with added image in map
    assert cut.onto.Pain.can_be_inhibited_byximage_3rqffo150j4thev5vlag2sgcu6_extension_png_xrelation[
               0] == cut.onto.Serotoninximage_3mt6o6tf2k523mssdhbrvb5fvm_extension_png
    # Edge in ontology must reflect edge with added media and node with aded media in map
    assert getattr(cut.onto.Pain, relation_class_from_content(TopicContentDto(
        title='triggered by', media=cts.PATH_NEW_MEDIA_TEMPORARY)))[0] == getattr(cut.onto, class_from_content(
        TopicContentDto(title='nociceptors', media=cts.PATH_NEW_MEDIA_TEMPORARY)))
    # Smr world changes:
    # Nodes in smr world must reflect changes in nodes in sheet "biological psychology"
    assert_that([n['xmind_node'].content for n in cut.smr_world.get_xmind_nodes_in_sheet(
        cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID).values()]).contains(
        *[TopicContentDto(title=t) for t in ('answer 1', 'answer 2', 'answer 2.1', 'answer 3.1')],
        TopicContentDto(image='attachments/3mt6o6tf2k523mssdhbrvb5fvm.png', title='Serotonin'),
        TopicContentDto(media=cts.PATH_NEW_MEDIA_TEMPORARY, title='nociceptors'))
    # Sheets in smr world must reflect sheet changes in imported xmind files
    assert_that([r.name for r in cut.smr_world._get_records('select * from main.xmind_sheets')]).contains(
        'biological psychology', 'general psychology', 'New sheet')
    # Nodes in smr world must reflect changes in nodes in sheet "new sheet"
    assert_that([r['xmind_node'].content for r in cut.smr_world.get_xmind_nodes_in_sheet(
        cts.NEW_SHEET_SHEET_ID).values()]).contains(*[TopicContentDto(title=t) for t in (
        'New sheet', 'first new sheet topic', 'another one', 'yet another one', 'answer to this other question',
        'yet another answer')])
    # Edges in smr world must reflect changes in the reference field due to moved nodes (here "enzymes" was moved
    # to be a sibling of "biogenic amines"
    assert cut.smr_world.get_smr_note_reference_fields([cts.EXAMPLE_IMAGE_EDGE_ID])[cts.EXAMPLE_IMAGE_EDGE_ID][
           :186] == cut.smr_world.get_smr_note_reference_fields([cts.COMPLETELY_UNRELATED_ANIMATION_EDGE_ID])[
                        cts.COMPLETELY_UNRELATED_ANIMATION_EDGE_ID][:186]
    # All nodes and edges in the smr world must be mapped to a concept or relation in the ontology
    # Anki collection changes:
    assert cut.smr_world._get_records("""select storid from main.xmind_nodes where storid is null 
        union select storid from main.xmind_edges where storid is null""") == []
    # Tags in anki collection must reflect sheet changes in imported xmind files
    assert_that(cut.col.tags.all()).contains_only(
        'testdeck::example_general_psychology::general_psychology', 'testdeck::example_map::biological_psychology',
        'testdeck::example_map::New_sheet')
    # Notes in anki collection must reflect new edges in sheet "new sheet"
    assert len(cut.col.findNotes('New_Sheet')) == 3
    # Note in anki collection must reflect added media in node and edge in map:
    assert all(cts.NEW_MEDIA_NAME in field for field in get_fields_by_question('triggered by*')[1:3])
    # Cards in anki collection must reflect removed nodes in the map
    assert len(cut.col.find_cards('Question:affects')) == 2
    # Notes in anki collection must reflect changes in order numbers in the map
    assert get_field_by_identifier(get_fields_by_question('modulated by*'), 'id') == '{{{'
    # Notes in anki must contain nodes that were moved to them as answers
    assert [get_field_by_identifier(get_fields_by_question("types"), 'a' + f) for f in ['1', '2']] == [
        'biogenic amines', 'enzymes']
    # Notes in anki collection must be removed if the respective edges were set empty in the map
    assert len(cut.col.findNotes('Reference:"*information transfer and processing</li>"')) == 2
    assert cut.onto.another_one.question_following_these_multiple_answers_xrelation == [cut.onto.yet_another_answer]
    assert_that([c.new_question_following_multiple_answers_xrelation for c in [
        cut.onto.Margret, cut.onto.new_answer]]).is_length(2).contains_only([cut.onto.answer_following_mult_answers])
    assert cut.onto.enzymes.example_xrelation == []
    assert cut.col.findNotes('enzymes example') == []
    assert cut.onto.neurotransmitters_changed_textximage_629d18n2i73im903jkrjmr98fg_extension_png.types_xrelation == [
        cut.onto.biogenic_amines, cut.onto.enzymes]
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
    assert cut.col.getNote(cut.col.findNotes('can be inhibited by')[0]).fields[
               1] == 'can be inhibited by<br><img src="attachments3rqffo150j4thev5vlag2sgcu6.png">'
    assert cut.col.getNote(cut.col.findNotes('Question:"for example"')[0])

# TODO: Change ontology to smr world mapping by introducing storids again (this will make it much easier to restore
#  the integrity of the smr world and ontology in case of inconsistencies)
# TODO: add file selection dialog if file was not found
# TODO: add log entries for changes made
# TODO: show log after sync
# TODO: make sure xmind sheets are updated after remote sync
# TODO: create triggers for collecting old image and media entries after removals: like this:
#  CREATE TRIGGER delete_xmind_media_on_delete_nodes
#     AFTER DELETE
#     ON xmind_nodes
#     WHEN not EXISTS(select *
#                      from xmind_nodes
#                      where link = OLD.link
#                      union
#                      select *
#                      from xmind_edges
#                      where link = OLD.link)
# BEGIN
#     ...
# END;