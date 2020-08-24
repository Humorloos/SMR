import re

from smr import consts as cts
from smr.dto.nodecontentdto import NodeContentDto


class FieldTranslator:
    def __init__(self):
        self.field_re_dict = {
            'ximage_': '<img src="',
            'xmedia_': '[sound:',
            'xlparenthesis_': '(',
            '_xrparenthesis': ')',
        }
        self.field_regex = re.compile("(%s)" % "|".join(self.field_re_dict.keys()))
        self.inverse_dict = {re.escape(self.field_re_dict[k]): k for k in self.field_re_dict}
        self.inverse_regex = re.compile("(%s)" % "|".join(self.inverse_dict.keys()))

    def class_from_content(self, content: NodeContentDto) -> str:
        """
        converts a node content dictionary into a string that can be used as an ontology class name
        :param content: xmind node content DTO
        :return: a class name generated from the node's content
        """
        classified: str = content.title.replace(" ", "_")
        if content.image:
            classified += "ximage_" + re.sub('attachments/', '', content.image)
            classified = re.sub('(\\.)(' + '|'.join(cts.X_IMAGE_EXTENSIONS) + ')', '_extension_\\2', classified)
        if content.media:
            classified += "xmedia_" + re.sub('attachments/', '', content.media)
            classified = re.sub('(\\.)(' + '|'.join(cts.X_MEDIA_EXTENSIONS) + ')', '_extension_\\2', classified)
        classified = self.inverse_regex.sub(lambda mo: self.inverse_dict[re.escape(mo.string[mo.start():mo.end()])],
                                            classified)
        return classified

    def relation_class_from_content(self, content: NodeContentDto) -> str:
        """
        converts a node content dictionary into a string that can be used as an ontology class name for a
        relationship property (only difference to concepts is postfix "_xrelation"
        :param content: xmind node content DTO
        :return: a class name generated from the node's content
        """
        return self.class_from_content(content) + "_xrelation"