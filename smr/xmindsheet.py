from typing import Dict

from bs4 import Tag

from smr.cachedproperty import cached_property
from smr.consts import X_MAX_ANSWERS
from smr.xmindtopic import XmindNode, XmindEdge


class MapError(Exception):
    """
    Exception that occurs when something is wrong with the map in an xmind sheet
    """

    def __init__(self, message):
        self.message = message


class XmindSheet:
    """
    Represents a sheet in an xmind file
    """

    def __init__(self, tag: Tag, file_path: str):
        self.tag = tag
        self.file_path = file_path

    @property
    def nodes(self) -> Dict[str, XmindNode]:
        try:
            return self.__dict__['nodes']
        except KeyError:
            self._set_nodes_and_edges()
            return self.nodes

    @property
    def edges(self) -> Dict[str, XmindEdge]:
        try:
            return self.__dict__['edges']
        except KeyError:
            self._set_nodes_and_edges()
            return self.edges

    @cached_property
    def root_node(self) -> XmindNode:
        return XmindNode(tag=self.tag.topic, file_path=self.file_path, sheet_id=self.id, order_number=1)

    @cached_property
    def name(self) -> str:
        return self.tag('title', recursive=False)[0].text

    @cached_property
    def last_modified(self) -> int:
        return int(self.tag['timestamp'])

    @cached_property
    def id(self):
        return self.tag['id']

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
            sheet.check_edge_integrity(edge)
            sheet.edges[edge.id] = edge
            for node in edge.child_nodes:
                _append_node(sheet, node)

        self.__dict__['nodes'] = {}
        self.__dict__['edges'] = {}
        _append_node(self, self.root_node)

    def check_edge_integrity(self, edge: XmindEdge):
        """
        checks whether the specified edge violates constraints specified by the smr addon (edges must be followed by
        nodes and may not have more than 20 answers
        :param edge: the edge to check the integrity of
        :return:
        """
        if len(edge.non_empty_child_nodes) > X_MAX_ANSWERS:
            raise MapError(f"""\
Warning:
A Question titled "{edge.title}" in map "{self.name}", file "{self.file_path}" (reference: {edge.get_reference()}) \
has more than {X_MAX_ANSWERS} answers.""")
        if len(edge.child_nodes) == 0:
            raise MapError(f"""\
Warning:
A Question titled "{edge.title}" in map "{self.name}", file "{self.file_path}" (reference: {edge.get_reference()}) is \
missing answers.""")
