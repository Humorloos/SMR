from typing import List, Dict

from bs4 import Tag


class XmindSheet:
    """
    Represents a sheet in an xmind file
    """
    def __init__(self, tag: Tag):
        self.tag = tag
        self.root_node = None
        self.nodes = None
        self.edges = None
        self.name = None
        self.last_modified = None

    @property
    def tag(self) -> Tag:
        return self._tag

    @tag.setter
    def tag(self, value: Tag):
        self._tag = value

    @property
    def nodes(self) -> Dict[str, Tag]:
        if self._nodes is None:
            self._set_nodes_and_edges()
        return self._nodes

    @nodes.setter
    def nodes(self, value: Dict[str, Tag]):
        self._nodes = value

    @property
    def edges(self) -> Dict[str, Tag]:
        if self._edges is None:
            self._set_nodes_and_edges()
        return self._edges

    @edges.setter
    def edges(self, value: Dict[str, Tag]):
        self._edges = value

    @property
    def root_node(self) -> Tag:
        if not self._root_node:
            self.root_node = self.tag.topic
        return self._root_node

    @root_node.setter
    def root_node(self, value: Tag):
        self._root_node = value

    @property
    def name(self) -> str:
        if not self._name:
            self.name = self.tag('title', recursive=False)[0].text
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def last_modified(self) -> int:
        if not self._last_modified:
            self.last_modified = int(self.tag['timestamp'])
        return self._last_modified

    @last_modified.setter
    def last_modified(self, value: int):
        self._last_modified = value

    def _set_nodes_and_edges(self):
        """
        Recursively walks through the whole map collects all nodes and edges and indexes them in the respective
        dictionaries
        """
        def _append_node(sheet, node: Tag):
            sheet.nodes[node['id']] = node
            for edge in get_child_nodes(node):
                _append_edge(sheet, edge)

        def _append_edge(sheet, edge: Tag):
            sheet.edges[edge['id']] = edge
            for node in get_child_nodes(edge):
                _append_node(sheet, node)
        self._nodes = {}
        self._edges = {}
        _append_node(self, self.root_node)


def get_child_nodes(tag: Tag) -> List[Tag]:
    """
    Gets all nodes directly following the node represented by the specified tag
    :param tag: the tag representing the node to get the child nodes for
    :return: the child nodes as a list of tags, an empty list if it doesn't have any
    """
    try:
        return tag.find('children', recursive=False).find(
            'topics', recursive=False).find_all('topic', recursive=False)
    except AttributeError:
        return []
