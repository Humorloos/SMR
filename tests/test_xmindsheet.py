from zipfile import ZipFile

from bs4 import BeautifulSoup

import tests.constants as cts
import pytest

from smr.xmindsheet import XmindSheet, get_child_nodes
from tests import constants as cts


@pytest.fixture
def xmind_sheet():
    with ZipFile(cts.PATH_EXAMPLE_MAP_DEFAULT, 'r') as file:
        sheet = BeautifulSoup(file.read(cts.NAME_CONTENT))('sheet')[0]
    yield XmindSheet(sheet)


def test_xmind_sheet(xmind_sheet, mocker):
    # given
    mocker.spy(xmind_sheet, '_set_nodes_and_edges')
    # then
    assert len(xmind_sheet.nodes) == 30
    assert len(xmind_sheet.edges) == 22
    assert xmind_sheet._set_nodes_and_edges.call_count == 1


def test_get_child_nodes(xmind_sheet):
    # when
    child_nodes = get_child_nodes(xmind_sheet.edges[cts.CONSIST_OF_EDGE_ID])
    # then
    assert child_nodes[0]['id'] == cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID
