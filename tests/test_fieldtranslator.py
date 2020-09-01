from smr.dto.topiccontentdto import TopicContentDto
from smr.fieldtranslator import class_from_content
from tests import constants as cts


def test_class_from_content():
    # given
    expected_class = 'biological_psychology'
    content = TopicContentDto(title="biological psychology")
    # when
    ontology_class = class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_image():
    # given
    expected_class = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
    content = TopicContentDto(image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI)
    # when
    ontology_class = class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_only_media():
    # given
    expected_class = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
    content = TopicContentDto(media="attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3")
    # when
    ontology_class = class_from_content(content)
    # then
    assert ontology_class == expected_class


def test_class_from_content_parentheses():
    # given
    expected_class = 'biological_psychology_xlparenthesis_text_in_parenthses_xrparenthesis'
    content = TopicContentDto(title="biological psychology (text in parenthses)")
    # when
    ontology_class = class_from_content(content)
    # then
    assert ontology_class == expected_class
