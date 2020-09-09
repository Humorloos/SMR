from zipfile import ZipFile

from bs4 import BeautifulSoup

import pytest

from smr.xmindsheet import XmindSheet
from tests import constants as cts


@pytest.fixture
def xmind_sheet():
    with ZipFile(cts.PATH_EXAMPLE_MAP_DEFAULT, 'r') as file:
        sheet = BeautifulSoup(file.read(cts.NAME_CONTENT))('sheet')[0]
    yield XmindSheet(tag=sheet, file_path=cts.PATH_EXAMPLE_MAP_TEMPORARY)


def test_xmind_sheet(xmind_sheet, mocker):
    # given
    mocker.spy(xmind_sheet, '_set_nodes_and_edges')
    # then
    assert len(xmind_sheet.nodes) == 34
    assert len(xmind_sheet.edges) == 25
    assert xmind_sheet._set_nodes_and_edges.call_count == 1


