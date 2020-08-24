import pytest

from smr.dto.nodecontentdto import NodeContentDto
from smr.fieldtranslator import FieldTranslator
from tests import constants as cts


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