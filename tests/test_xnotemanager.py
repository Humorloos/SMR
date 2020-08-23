import pytest

import tests.constants as cts
from smr.dto.nodecontentdto import NodeContentDto
from smr.xnotemanager import FieldTranslator, XNoteManager, image_from_field, media_from_field, title_from_field, content_from_field, \
    field_from_content
from smr.smrworld import sort_id_from_order_number


@pytest.fixture
def field_translator():
    yield FieldTranslator()


def test_class_from_content(field_translator):
    # given
    expected_class = 'biological_psychology'
    content = NodeContentDto(title="biological psychology")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_image(field_translator):
    # given
    expected_class = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
    content = NodeContentDto(image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI)
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_media(field_translator):
    # given
    expected_class = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
    content = NodeContentDto(media="attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_parentheses(field_translator):
    # given
    expected_class = 'biological_psychology_xlparenthesis_text_in_parenthses_xrparenthesis'
    content = NodeContentDto(title="biological psychology (text in parenthses)")
    # when
    ontology_class = field_translator.class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_sort_id_from_order_number():
    # when
    sort_ids = [sort_id_from_order_number(i) for i in range(1, 21)]
    # then
    assert sort_ids == sorted(sort_ids)


@pytest.fixture
def note_manager(collection_with_example_map):
    yield XNoteManager(collection_with_example_map)


def test_image_from_field(smr_world_with_example_map):
    # when
    image = image_from_field('MAO is not a neurotransmitter[sound:serotonin.mp3]<br><img '
                             'src="attachments629d18n2i73im903jkrjmr98fg.png">', smr_world_with_example_map)
    # then
    assert image == 'attachments/629d18n2i73im903jkrjmr98fg.png'


def test_image_from_field_image_not_registered(smr_world_with_example_map):
    # when
    image = image_from_field('no image<img src="some_image.png">', smr_world_with_example_map)
    # then
    assert image == "some_image.png"


def test_image_from_field_image_no_image(smr_world_with_example_map):
    # when
    image = image_from_field('note title', smr_world_with_example_map)
    # then
    assert image is None


def test_media_from_field(smr_world_with_example_map):
    # when
    media = media_from_field('MAO is not a neurotransmitter[sound:serotonin.mp3]<br><img '
                             'src="attachments629d18n2i73im903jkrjmr98fg.png">', smr_world_with_example_map)
    # then
    assert media == cts.PATH_HYPERLINK_MEDIA_TEMPORARY


def test_media_from_field_no_media(smr_world_with_example_map):
    # when
    media = media_from_field('no image', smr_world_with_example_map)
    # then
    assert media is None


def test_get_actual_deck_names_and_ids(note_manager):
    # when
    deck_names_and_ids = note_manager.get_actual_deck_names_and_ids()
    decks = [(d.id, d.name) for d in deck_names_and_ids]
    assert decks[0] == (1, 'Default')
    assert decks[1][1] == 'testdeck'


def test_title_from_field():
    # when
    title = title_from_field('MAO is not a neurotransmitter[sound:serotonin.mp3]<img '
                             'src="attachments629d18n2i73im903jkrjmr98fg.png">')
    # then
    assert title == 'MAO is not a neurotransmitter'


def test_title_from_field_with_html_tags():
    title = title_from_field('enzymes<div><img src="paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg"><br></div>')
    # then
    assert title == "enzymes"


def test_content_from_field(smr_world_with_example_map):
    # when
    content = content_from_field('MAO is not a neurotransmitter[sound:serotonin.mp3]<img '
                                 'src="attachments629d18n2i73im903jkrjmr98fg.png">', smr_world_with_example_map)
    # then
    assert content == NodeContentDto(image='attachments/629d18n2i73im903jkrjmr98fg.png',
                                     media=cts.PATH_HYPERLINK_MEDIA_TEMPORARY,
                                     title='MAO is not a neurotransmitter')


def test_field_from_content(smr_world_with_example_map):
    # when
    field = field_from_content(content=cts.NEUROTRANSMITTERS_NODE_CONTENT, smr_world=smr_world_with_example_map)
    # then
    assert field == 'neurotransmitters<br><img src="attachments629d18n2i73im903jkrjmr98fg.png">'
