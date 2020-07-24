# class TestGetNodeImg(TestXManager):
#     def test_no_image(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = get_node_image(tag)
#         self.assertEqual(act, None)
#
#
# class TestGetNodeHyperlink(TestXManager):
#     def test_no_hyperlink(self):
#         with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
#                                'sheet_biological_psychology.xml'), 'r') as file:
#             tag = BeautifulSoup(file.read(), features='html.parser').topic
#         act = get_node_hyperlink(tag)
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
import test.constants as cts
import bs4

from main.dto.nodecontentdto import NodeContentDTO
from main.xmanager import is_empty_node, get_node_title, get_child_nodes, get_non_empty_sibling_nodes, get_parent_node, \
    get_node_content, get_node_image, get_node_hyperlink


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


def test_get_tag_by_id(tag_for_tests, x_manager):
    # given
    expexted_tag = tag_for_tests
    # when
    tag = x_manager.get_tag_by_id(expexted_tag['id'])
    # then
    assert tag.contents[0].text == expexted_tag.contents[1].text


def test_get_node_content(tag_for_tests):
    # when
    node_content = get_node_content(tag=tag_for_tests)
    # then
    assert node_content.title == 'biological psychology'
    assert node_content.image is None
    assert node_content.media is None


def test_get_node_content_with_image(x_manager):
    # given
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_XMIND_ID)
    # when
    node_content = get_node_content(tag=tag)
    # then
    assert node_content == cts.NEUROTRANSMITTERS_NODE_CONTENT


def test_get_node_content_with_media(x_manager):
    # given
    tag = x_manager.get_tag_by_id('1s7h0rvsclrnvs8qq9u71acml5')
    # when
    node_content = get_node_content(tag=tag)
    # then
    assert node_content == NodeContentDTO(media='attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3')


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
    # then
    assert [c.contents[1].text for c in child_nodes] == expected_child_node_titles


def test_get_parent_node(x_manager):
    # given
    expected_parent = "splits up"
    # when
    parent_node = get_parent_node(x_manager.get_tag_by_id(cts.EMPTY_NODE_TAG_ID))
    # then
    assert parent_node.contents[0].text == expected_parent


def test_get_non_empty_sibling_nodes(x_manager):
    # given
    expected_siblings = ['Serotonin', 'dopamine', 'adrenaline', 'noradrenaline']
    # when
    sibling_nodes = get_non_empty_sibling_nodes(x_manager.get_tag_by_id(cts.EMPTY_NODE_TAG_ID))
    # then
    assert [n.contents[0].text for n in sibling_nodes] == expected_siblings


def test_get_node_image(x_manager):
    # given
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_XMIND_ID)
    # when
    node_image = get_node_image(tag)
    # then
    assert node_image == 'xap:attachments/629d18n2i73im903jkrjmr98fg.png'


def test_get_node_hyperlink(x_manager):
    # given
    tag = x_manager.get_tag_by_id('1s7h0rvsclrnvs8qq9u71acml5')
    # when
    node_media = get_node_hyperlink(tag)
    # then
    assert node_media == 'xap:attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3'