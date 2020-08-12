import pytest

from main.dto.nodecontentdto import NodeContentDTO
from main.xnotemanager import FieldTranslator, get_smr_note_reference_fields, get_smr_note_sort_field, \
    sort_id_from_order_number, XNoteManager, image_from_field
import test.constants as cts


@pytest.fixture
def field_translator():
    yield FieldTranslator()


def test_class_from_content(field_translator):
    # given
    expected_class = 'biological_psychology'
    content = NodeContentDTO(title="biological psychology")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_image(field_translator):
    # given
    expected_class = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
    content = NodeContentDTO(image="attachments/09r2e442o8lppjfeblf7il2rmd.png")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_media(field_translator):
    # given
    expected_class = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
    content = NodeContentDTO(media="attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_parentheses(field_translator):
    # given
    expected_class = 'biological_psychology_xlparenthesis_text_in_parenthses_xrparenthesis'
    content = NodeContentDTO(title="biological psychology (text in parenthses)")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_get_smr_note_reference_fields(smr_world_for_tests):
    # when
    reference_fields = get_smr_note_reference_fields(
        smr_world=smr_world_for_tests, edge_ids=[
            cts.PRONOUNCIATION_EDGE_XMIND_ID, cts.EDGE_WITH_MEDIA_XMIND_ID,
            cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID, "7ipkhjdorhgcasdf12asd123ga"])
    # then
    assert reference_fields == {
        '4s27e1mvsb5jqoiuaqmnlo8m71': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>requires: neurotransmitters <img '
                                      'src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic '
                                      'amines</li><li><img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: '
                                      'Serotonin</li>',
        '6iivm8tpoqj2c0euaabtput14l': 'biological psychology<li>investigates: information transfer and '
                                      'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits '
                                      'up: Serotonin, dopamine, adrenaline, noradrenaline</li>',
        '7ipkhjdorhgcasdf12asd123ga': 'biological psychology<li>investigates: perception</li><li>Pain</li><li>some '
                                      'media edge title (media): answer to some media edge</li>',
        '7ite3obkfmbcasdf12asd123ga': 'biological psychology<li>investigates: perception</li><li>Pain</li>'}


def test_get_smr_note_sort_field(smr_world_for_tests):
    # when
    sort_field = get_smr_note_sort_field(smr_world=smr_world_for_tests,
                                         edge_id=cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert sort_field == '|{|{{{|{'


def test_sort_id_from_order_number():
    # when
    sort_ids = [sort_id_from_order_number(i) for i in range(1, 21)]
    # then
    assert sort_ids == sorted(sort_ids)


@pytest.fixture
def note_manager(collection_4_migration):
    yield XNoteManager(collection_4_migration)


def test_image_from_field():
    # when
    image = image_from_field('MAO is not a neurotransmitter[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]<br><img '
                             'src="09r2e442o8lppjfeblf7il2rmd.png">')
    # then
    assert image == '09r2e442o8lppjfeblf7il2rmd.png'


def test_image_from_field_no_image():
    # when
    image = image_from_field('no image')
    # then
    assert image is None
