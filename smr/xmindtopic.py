from __future__ import annotations

import os
from abc import ABC
from typing import List, Optional, Tuple
from urllib.parse import unquote

from bs4 import Tag, BeautifulSoup

from smr import fieldtranslator
from smr.cachedproperty import cached_property
from smr.consts import X_MEDIA_EXTENSIONS
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindtopicdto import XmindTopicDto


class XmindTopic(ABC):
    """
    abstract basic implementation of xmind topics (edges or nodes)
    """

    def __init__(self, tag: Tag, sheet_id: str, file_path: str, order_number: int):
        self.tag = tag
        self.sheet_id = sheet_id
        self.file_path = file_path
        self.order_number = order_number

    @cached_property
    def hyperlink(self) -> str:
        try:
            return self.tag['xlink:href']
        except KeyError:
            return ''

    @cached_property
    def hyperlink_uri(self):
        if self.hyperlink == '':
            return ''
        else:
            # for embedded media, return the relative path
            if not self.hyperlink.startswith('file'):
                return self.hyperlink[4:]
            # for media that was referenced via hyperlink, return an absolute path
            else:
                if self.hyperlink[5:7] == "//":
                    return os.path.normpath(unquote(self.hyperlink[7:]))
                # for media with relative path, also get an absolute path
                else:
                    return os.path.join(os.path.split(self.file_path)[0], unquote(self.hyperlink[5:]))

    @cached_property
    def image_tag(self) -> Optional[Tag]:
        return self.tag.find('xhtml:img', recursive=False)

    @cached_property
    def title_tag(self) -> Tag:
        return self.tag.find('title', recursive=False)

    @cached_property
    def image(self) -> Optional[str]:
        if self.image_tag:
            return self.image_tag['xhtml:src'][4:]
        else:
            return None

    @image.setter
    def image(self, image: str):
        if self.image_tag is None:
            del self.image_tag
            image_tag = self.soup.new_tag(name='xhtml:img', align='bottom')
            self.tag.append(image_tag)
        self.image_tag['xhtml:src'] = 'xap:' + image
        del self.__dict__['image']
        del self.content

    @image.deleter
    def image(self):
        if self.image_tag is not None:
            self.image_tag.decompose()
        del self.image_tag
        del self.content
        del self.dto

    @cached_property
    def title(self) -> str:
        try:
            return self.title_tag.text
        except AttributeError:
            return ''

    @title.setter
    def title(self, title: str):
        if self.title == '':
            del self.title_tag
            title_tag = self.soup.new_tag(name='title')
            self.tag.append(title_tag)
        self.title_tag.string = title
        del self.__dict__['title']
        del self.content

    @title.deleter
    def title(self):
        self.title_tag.decompose()
        del self.title_tag
        del self.content
        del self.dto

    @cached_property
    def media(self) -> Optional[str]:
        if self.hyperlink_uri.endswith(X_MEDIA_EXTENSIONS):
            return self.hyperlink_uri
        else:
            return None

    @cached_property
    def content(self) -> TopicContentDto:
        return TopicContentDto(image=self.image, media=self.media, title=self.title)

    @content.deleter
    def content(self):
        del self.content_string
        del self.is_empty

    @cached_property
    def is_empty(self) -> bool:
        return self.content.is_empty()

    @cached_property
    def id(self) -> str:
        return self.tag['id']

    @cached_property
    def soup(self):
        return BeautifulSoup(features="html.parser")

    @cached_property
    def content_string(self) -> str:
        return self.content.to_string()

    @cached_property
    def child_topic_tags_and_order_numbers(self) -> List[Tuple[Tag, int]]:
        try:
            return [(tag, i) for i, tag in enumerate(
                self.tag.find('children', recursive=False).find('topics', recursive=False).find_all(
                    'topic', recursive=False), start=1)]
        except AttributeError:
            return []

    @cached_property
    def dto(self) -> XmindTopicDto:
        return XmindTopicDto(node_id=self.id, sheet_id=self.sheet_id, title=self.title, image=self.image,
                             link=self.media, order_number=self.order_number)

    def decompose(self):
        """
        Destroys the tag associated with this node
        """
        self.tag.decompose()


class XmindEdge(XmindTopic):
    def __init__(self, tag: Tag, sheet_id: str, file_path: str, order_number: int, direct_parent_node: 'XmindNode'):
        super().__init__(tag=tag, file_path=file_path, sheet_id=sheet_id, order_number=order_number)
        self.direct_parent_node = direct_parent_node

    @cached_property
    def child_nodes(self) -> List['XmindNode']:
        return [XmindNode(tag=tag, sheet_id=self.sheet_id, file_path=self.file_path, order_number=i, parent_edge=self)
                for tag, i in self.child_topic_tags_and_order_numbers]

    @cached_property
    def non_empty_child_nodes(self) -> List['XmindNode']:
        return [n for n in self.child_nodes if not n.is_empty]

    @cached_property
    def parent_nodes(self) -> List[XmindNode]:
        if self.direct_parent_node.is_empty:
            return self.direct_parent_node.non_empty_sibling_nodes
        else:
            return [self.direct_parent_node]

    @cached_property
    def relation_class_name(self) -> str:
        if self.is_empty:
            return fieldtranslator.CHILD_RELATION_NAME
        else:
            return fieldtranslator.relation_class_from_content(self.content)

    @cached_property
    def sibling_edges(self) -> List[XmindEdge]:
        return self.parent_nodes[0].child_edges

    @XmindTopic.is_empty.deleter
    def is_empty(self):
        XmindTopic.is_empty.__delete__(self)
        del self.relation_class_name

    def get_reference(self, reference: str = '') -> str:
        """
        Gets the reference without filenames for this edge
        :param reference: content strings of all prior topics arranged to a reference
        :return: the reference
        """
        if self.parent_nodes[0].parent_edge:
            reference = reference + self.parent_nodes[0].parent_edge.get_reference(reference)
            reference = reference + '\n' + self.parent_nodes[0].parent_edge.content_string + ': ' + \
                        ', '.join(n.content_string for n in self.parent_nodes)
        else:
            reference = reference + self.parent_nodes[0].content_string
        return reference


# noinspection PyAttributeOutsideInit
class XmindNode(XmindTopic):

    def __init__(self, tag: Tag, sheet_id: str, file_path: str, order_number: int,
                 parent_edge: Optional[XmindEdge] = None):
        self.parent_edge = parent_edge
        super().__init__(tag=tag, file_path=file_path, sheet_id=sheet_id, order_number=order_number)

    @property
    def order_number(self):
        if self.is_empty:
            return len(self.non_empty_sibling_nodes) + 1
        else:
            return self._order_number

    @order_number.setter
    def order_number(self, value: int):
        self._order_number = value

    @cached_property
    def child_edges(self) -> List[XmindEdge]:
        return [XmindEdge(tag=tag, sheet_id=self.sheet_id, file_path=self.file_path, order_number=i,
                          direct_parent_node=self) for tag, i in self.child_topic_tags_and_order_numbers]

    @cached_property
    def sibling_nodes(self) -> List[XmindNode]:
        if self.parent_edge is not None:
            return self.parent_edge.child_nodes
        else:
            return []

    @cached_property
    def non_empty_sibling_nodes(self) -> List[XmindNode]:
        return [node for node in self.sibling_nodes if not node.is_empty]
