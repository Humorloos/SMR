import os

import bs4

# class TestGetNodeImg(TestXManager):
#     def test_no_image(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = getNodeImg(tag)
#         self.assertEqual(act, None)
#
#
# class TestGetNodeHyperlink(TestXManager):
#     def test_no_hyperlink(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = getNodeHyperlink(tag)
#         self.assertEqual(act, None)
#
# class TestGetRemote(TestXManager):
#     def test_get_remote(self):
#         manager = self.xManager
#         act = manager.get_remote()
#         self.fail()
#
#
# class TestGetAnswerNodes(TestXManager):
#     def test_crosslink_answers(self):
#         manager = self.xManager
#         tag = manager.get_tag_by_id('4lrqok8ac9hec8u2c2ul4mpo4k')
#         act = manager.get_answer_nodes(tag)
#         self.fail()
#
#     def test_no_answers(self):
#         manager = self.xManager
#         tag = manager.get_tag_by_id('4s27e1mvsb5jqoiuaqmnlo8m71')
#         act = manager.get_answer_nodes(tag)
#         self.fail()
#
#
# class TestIsCrosslinkNode(TestXManager):
#     def test_media_node(self):
#         manager = self.xManager
#         tag = manager.get_tag_by_id('1s7h0rvsclrnvs8qq9u71acml5')
#         act = manager.is_crosslink_node(tag)
#         self.assertFalse(act)
#
import pytest
import XmindImport.tests.constants as cts
from xmanager import is_empty_node, get_node_title, get_child_nodes

def test_xmanager(x_manager):
    # given
    expected_sheets = ['biological psychology', 'clinical psychology', 'ref']
    expected_referenced_file = ['C:\\Users\\lloos\\OneDrive - bwedu\\Projects\\AnkiAddon\\anki-addon-dev\\addons21'
                                '\\XmindImport\\resources\\example_general_psychology.xmind']
    # when
    cut = x_manager
    # then
    assert list(cut.get_sheets().keys()) == expected_sheets
    assert cut.get_referenced_files() == expected_referenced_file


def test_get_root_node(x_manager):
    # given
    cut = x_manager
    # when
    root_node = cut.get_root_node(sheet="biological psychology")
    # then
    assert isinstance(root_node, bs4.element.Tag)


def test_is_empty_node(tag_for_tests):
    # when
    empty = is_empty_node(tag_for_tests)
    # then
    assert empty is False


def test_get_node_title(tag_for_tests):
    # when
    title = get_node_title(tag_for_tests)
    # then
    assert title == 'biological psychology'


def test_get_node_content(x_manager, tag_for_tests):
    # when
    node_content = x_manager.get_node_content(tag=tag_for_tests)
    # then
    assert node_content['content'] == 'biological psychology'
    assert node_content['media']['image'] is None
    assert node_content['media']['media'] is None


def test_get_tag_by_id(tag_for_tests, x_manager):
    # given
    expexted_tag = tag_for_tests
    # when
    tag = x_manager.get_tag_by_id(expexted_tag['id'])
    # then
    assert tag.contents[0].text == expexted_tag.contents[1].text


def test_get_node_content_with_image(x_manager):
    # given
    cut = x_manager
    tag = cut.get_tag_by_id(cts.NEUROTRANSMITTERS_XMIND_ID)
    # when
    node_content = cut.get_node_content(tag=tag)
    # then
    assert node_content == cts.NEUROTRANSMITTERS_NODE_CONTENT


def test_get_node_content_with_media(x_manager):
    # given
    cut = x_manager
    tag = cut.get_tag_by_id('1s7h0rvsclrnvs8qq9u71acml5')
    # when
    node_content = cut.get_node_content(tag=tag)
    # then
    assert node_content == {'content': '',
                            'media': {'image': None, 'media': 'attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3'}}


def test_get_sheet_id(x_manager):
    # when
    sheet_id = x_manager.get_sheet_id('biological psychology')
    # then
    assert sheet_id == '2485j5qgetfevlt00vhrn53961'


def test_get_child_nodes(tag_for_tests):
    # given
    expected_child_node_titles = ['', 'investigates']
    # when
    child_nodes = get_child_nodes(tag_for_tests)
    assert [c.contents[1].text for c in child_nodes] == expected_child_node_titles
