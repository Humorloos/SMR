from typing import Dict

from bs4 import Tag

from smr.xmindtopic import XmindNode, XmindEdge


class XmindSheet:
    """
    Represents a sheet in an xmind file
    """
    def __init__(self, tag: Tag, file_path: str):
        self.tag = tag
        self.file_path = file_path
        self.id = None
        self.root_node = None
        self.nodes = None
        self.edges = None
        self.name = None
        self.last_modified = None

    @property
    def file_path(self) -> str:
        return self._file_path

    @file_path.setter
    def file_path(self, value: str):
        self._file_path = value

    @property
    def tag(self) -> Tag:
        return self._tag

    @tag.setter
    def tag(self, value: Tag):
        self._tag = value

    @property
    def nodes(self) -> Dict[str, XmindNode]:
        if self._nodes is None:
            self._set_nodes_and_edges()
        return self._nodes

    @nodes.setter
    def nodes(self, value: Dict[str, Tag]):
        self._nodes = value

    @property
    def edges(self) -> Dict[str, XmindEdge]:
        if self._edges is None:
            self._set_nodes_and_edges()
        return self._edges

    @edges.setter
    def edges(self, value: Dict[str, XmindEdge]):
        self._edges = value

    @property
    def root_node(self) -> XmindNode:
        if not self._root_node:
            self.root_node = XmindNode(tag=self.tag.topic, file_path=self.file_path, sheet_id=self.id, order_number=1)
        return self._root_node

    @root_node.setter
    def root_node(self, value: XmindNode):
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

    @property
    def id(self):
        if not self._id:
            self._id = self.tag['id']
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    def _set_nodes_and_edges(self):
        """
        Recursively walks through the whole map, collects all nodes and edges and indexes them in the respective
        dictionaries
        """
        def _append_node(sheet: XmindSheet, node: XmindNode):
            sheet.nodes[node.id] = node
            for edge in node.child_edges:
                _append_edge(sheet, edge)

        def _append_edge(sheet: XmindSheet, edge: XmindEdge):
            sheet.edges[edge.id] = edge
            for node in edge.child_nodes:
                _append_node(sheet, node)
        self._nodes = {}
        self._edges = {}
        _append_node(self, self.root_node)


