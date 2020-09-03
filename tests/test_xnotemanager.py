import pytest
from assertpy import assert_that

import tests.constants as cts
from smr.dto.topiccontentdto import TopicContentDto
from smr.xnotemanager import XNoteManager, image_from_field, media_from_field, title_from_field, \
    content_from_field, \
    field_from_content


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
    assert content == TopicContentDto(image='attachments/629d18n2i73im903jkrjmr98fg.png',
                                      media=cts.PATH_HYPERLINK_MEDIA_TEMPORARY,
                                      title='MAO is not a neurotransmitter')


def test_field_from_content(smr_world_with_example_map):
    # when
    field = field_from_content(content=cts.NEUROTRANSMITTERS_NODE_CONTENT, smr_world=smr_world_with_example_map)
    # then
    assert field == 'neurotransmitters<br><img src="attachments629d18n2i73im903jkrjmr98fg.png">'


def test_clear_unused_tags(note_manager, smr_world_with_example_map):
    # given
    cut = note_manager
    cut.col.remove_notes(cut.col.find_notes('tag:testdeck::example_map::clinical_psychology'))
    # when
    cut.clear_unused_tags()
    # then
    assert_that(cut.col.tags.all()).contains_only(
        'testdeck::example_general_psychology::general_psychology', 'testdeck::example_map::biological_psychology')
