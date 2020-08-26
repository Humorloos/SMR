import os
import urllib
from abc import ABC
from typing import List, Optional

from bs4 import Tag, BeautifulSoup

from smr.consts import X_MEDIA_EXTENSIONS
from smr.dto.topiccontentdto import TopicContentDto


# noinspection PyAttributeOutsideInit
class XmindTopic(ABC):
    """
    abstract basic implementation of xmind topics (edges or nodes)
    """

    def __init__(self, tag, sheet_id, file_path):
        self._tag = tag
        self._sheet_id = sheet_id
        self._file_path = file_path
        self._title = None
        self._title_tag = None
        self._content = None
        self._content_string = None
        self._is_empty = None
        self._hyperlink = None
        self._hyperlink_uri = None
        self._id = None
        self._last_modified = None
        self._soup = None

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, value: str):
        self._file_path = value

    @property
    def sheet_id(self) -> str:
        return self._sheet_id

    @sheet_id.setter
    def sheet_id(self, value: str):
        self._sheet_id = value

    @property
    def tag(self) -> Tag:
        return self._tag

    @tag.setter
    def tag(self, value: Tag):
        self._tag = value

    @property
    def title_tag(self):
        if self._title_tag is None:
            self.title_tag = self.tag.find('title', recursive=False)
        return self._title_tag

    @title_tag.setter
    def title_tag(self, value):
        self._title_tag = value

    @property
    def title(self) -> str:
        if not self._title:
            try:
                self._title = self.title_tag.text
            except AttributeError:
                self._title = ''
        return self._title

    @title.setter
    def title(self, title: str):
        if self.title == '':
            self.title_tag = self.soup.new_tag(name='title')
            self.tag.append(self.title_tag)
        self.title_tag.string = title
        self._title = title
        self.content.title = self.title

    @property
    def hyperlink(self) -> str:
        if not self._hyperlink:
            try:
                self.hyperlink = self.tag['xlink:href']
            except KeyError:
                self.hyperlink = ''
        return self._hyperlink

    @hyperlink.setter
    def hyperlink(self, value: str):
        self._hyperlink = value

    @property
    def hyperlink_uri(self):
        if not self._hyperlink_uri:
            if self.hyperlink == '':
                self._hyperlink_uri = ''
            else:
                # for media that was referenced via hyperlink, return an absolute path
                if self.hyperlink.startswith('file'):
                    if self.hyperlink[5:7] == "//":
                        self._hyperlink_uri = os.path.normpath(urllib.parse.unquote(self.hyperlink[7:]))
                    # for media with relative path, also get an absolute path
                    else:
                        self._hyperlink_uri = os.path.join(
                            os.path.split(self.file_path)[0], urllib.parse.unquote(self.hyperlink[5:]))
                # for embedded media, return the relative path
                else:
                    self._hyperlink_uri = self.hyperlink[4:]
        return self._hyperlink_uri

    @hyperlink_uri.setter
    def hyperlink_uri(self, value: str):
        self._hyperlink_uri = value

    @property
    def image_tag(self):
        try:
            return self._image_tag
        except AttributeError:
            self._image_tag = self.tag.find('xhtml:img', recursive=False)
            return self._image_tag

    @image_tag.setter
    def image_tag(self, value: Tag):
        self._image_tag = value

    @property
    def image(self) -> str:
        try:
            return self._image
        except AttributeError:
            if self.image_tag:
                self._image = self.image_tag['xhtml:src'][4:]
            else:
                self._image = None
            return self._image

    @image.setter
    def image(self, image: str):
        if self.image_tag is None:
            self.image_tag = self.soup.new_tag(name='xhtml:img', align='bottom')
            self.tag.append(self.image_tag)
        self.image_tag['xhtml:src'] = 'xap:' + image
        self._image = image
        self.content.image = self.image

    @image.deleter
    def image(self):
        del self.image_tag
        del self._image

    @image_tag.deleter
    def image_tag(self):
        self.image_tag.decompose()
        del self._image_tag

    @property
    def media(self) -> str:
        try:
            return self._media
        except AttributeError:
            if self.hyperlink_uri.endswith(X_MEDIA_EXTENSIONS):
                self._media = self.hyperlink_uri
            else:
                self._media = None
            return self._media

    @media.setter
    def media(self, value: str):
        self._media = value

    @property
    def content(self) -> TopicContentDto:
        if not self._content:
            self._content = TopicContentDto(image=self.image, media=self.media, title=self.title)
        return self._content

    @content.setter
    def content(self, content: TopicContentDto):
        self._content = content

    @property
    def is_empty(self) -> bool:
        if self._is_empty is None:
            self._is_empty = self.content.is_empty()
        return self._is_empty

    @is_empty.setter
    def is_empty(self, value: bool):
        self._is_empty = value

    @property
    def id(self) -> str:
        if not self._id:
            self.id = self.tag['id']
        return self._id

    @id.setter
    def id(self, value: str):
        self._id = value

    @property
    def last_modified(self) -> int:
        if not self._last_modified:
            self._last_modified = int(self.tag['timestamp'])
        return self._last_modified

    @last_modified.setter
    def last_modified(self, value: int):
        self._last_modified = value

    @property
    def soup(self):
        if not self._soup:
            self.soup = BeautifulSoup()
        return self._soup

    @soup.setter
    def soup(self, value):
        self._soup = value

    @property
    def content_string(self) -> str:
        if not self._content_string:
            self._content_string = self.content.to_string()
        return self._content_string

    @content_string.setter
    def content_string(self, value: str):
        self._content_string = value

    def decompose(self):
        """
        Destroys the tag associated with this node
        """
        self.tag.decompose()

    def _get_child_topic_tags(self) -> List[Tag]:
        """
        Gets all topics directly following the topic
        :return: the child topics as a list of tags, an empty list if it doesn't have any
        """
        try:
            return self.tag.find('children', recursive=False).find('topics', recursive=False).find_all('topic',
                                                                                                       recursive=False)
        except AttributeError:
            return []

    def _get_parent_topic_tag(self) -> Optional[Tag]:
        """
        gets the tag representing the parent topic
        :return: the tag representing the parent topic, None if the topic is the root node of the map
        """
        parent_topic_tag = self.tag.parent.parent.parent
        if type(parent_topic_tag) == Tag:
            return parent_topic_tag
        else:
            return


class XmindEdge(XmindTopic):
    def __init__(self, tag: Tag, sheet_id: str, file_path: str, direct_parent_node: 'XmindNode'):
        super().__init__(tag=tag, file_path=file_path, sheet_id=sheet_id)
        self.direct_parent_node = direct_parent_node
        self.child_nodes = None
        self.parent_nodes = None

    @property
    def child_nodes(self) -> List['XmindNode']:
        if self._child_nodes is None:
            self.child_nodes = [XmindNode(tag=tag, sheet_id=self.sheet_id, file_path=self.file_path, parent_edge=self)
                                for tag in self._get_child_topic_tags()]
        return self._child_nodes

    @child_nodes.setter
    def child_nodes(self, value: List['XmindNode']):
        self._child_nodes = value

    @property
    def parent_nodes(self) -> List['XmindNode']:
        if not self._parent_nodes:
            if self.direct_parent_node.is_empty:
                self.parent_nodes = self.direct_parent_node.non_empty_sibling_nodes
            else:
                self.parent_nodes = [self.direct_parent_node]
        return self._parent_nodes

    @parent_nodes.setter
    def parent_nodes(self, value: List['XmindNode']):
        self._parent_nodes = value

    @property
    def direct_parent_node(self) -> 'XmindNode':
        return self._direct_parent_node

    @direct_parent_node.setter
    def direct_parent_node(self, value: 'XmindNode'):
        self._direct_parent_node = value

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


class XmindNode(XmindTopic):

    def __init__(self, tag: Tag, sheet_id: str, file_path: str, parent_edge: Optional[XmindEdge] = None):
        super().__init__(tag=tag, file_path=file_path, sheet_id=sheet_id)
        self.child_edges = None
        self.non_empty_sibling_nodes = None
        self.parent_edge = parent_edge

    @property
    def child_edges(self) -> List[XmindEdge]:
        if not self._child_edges:
            self.child_edges = [XmindEdge(tag=tag, sheet_id=self.sheet_id, file_path=self.file_path,
                                          direct_parent_node=self) for tag in
                                self._get_child_topic_tags()]
        return self._child_edges

    @child_edges.setter
    def child_edges(self, value: List[XmindEdge]):
        self._child_edges = value

    @property
    def non_empty_sibling_nodes(self) -> List['XmindNode']:
        if self._non_empty_sibling_nodes is None:
            self.non_empty_sibling_nodes = [node for node in self.parent_edge.child_nodes if not node.is_empty]
        return self._non_empty_sibling_nodes

    @non_empty_sibling_nodes.setter
    def non_empty_sibling_nodes(self, value: List['XmindNode']):
        self._non_empty_sibling_nodes = value

    @property
    def parent_edge(self) -> Optional[XmindEdge]:
        return self._parent_edge

    @parent_edge.setter
    def parent_edge(self, value: Optional[XmindEdge]):
        self._parent_edge = value
