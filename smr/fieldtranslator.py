import re

from smr import consts as cts
from smr.dto.topiccontentdto import TopicContentDto

FIELD_RE_DICT = {
    'ximage_': '<img src="',
    'xmedia_': '[sound:',
    'xlparenthesis_': '(',
    '_xrparenthesis': ')',
}
FIELD_REGEX = re.compile("(%s)" % "|".join(FIELD_RE_DICT.keys()))
INVERSE_DICT = {re.escape(FIELD_RE_DICT[k]): k for k in FIELD_RE_DICT}
INVERSE_REGEX = re.compile("(%s)" % "|".join(INVERSE_DICT.keys()))
CHILD_NAME = 'smrchild'
PARENT_NAME = 'smrparent'


def class_from_content(content: TopicContentDto) -> str:
    """
    converts a node content dictionary into a string that can be used as an ontology class name
    :param content: xmind node content DTO
    :return: a class name generated from the node's content
    """
    classified: str = content.title.replace(" ", "_")
    if content.image:
        classified += "ximage_" + re.sub('attachments/', '', content.image.replace(" ", "_"))
        classified = re.sub('(\\.)(' + '|'.join(cts.X_IMAGE_EXTENSIONS) + ')', '_extension_\\2', classified)
    if content.media:
        classified += "xmedia_" + re.sub('attachments/', '', content.media.replace(" ", "_"))
        classified = re.sub('(\\.)(' + '|'.join(cts.X_MEDIA_EXTENSIONS) + ')', '_extension_\\2', classified)
    classified = INVERSE_REGEX.sub(lambda mo: INVERSE_DICT[re.escape(mo.string[mo.start():mo.end()])],
                                   classified)
    return classified


def relation_class_from_content(content: TopicContentDto) -> str:
    """
    converts a node content dictionary into a string that can be used as an ontology class name for a
    relationship property (only difference to concepts is postfix "_xrelation"
    :param content: xmind node content DTO
    :return: a class name generated from the node's content
    """
    return class_from_content(content) + "_xrelation"


PARENT_RELATION_NAME = relation_class_from_content(TopicContentDto(title=PARENT_NAME))
CHILD_RELATION_NAME = relation_class_from_content(TopicContentDto(title=CHILD_NAME))
