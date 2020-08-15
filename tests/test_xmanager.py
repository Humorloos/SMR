import bs4
import pytest

import tests.constants as cts
from smr.xmanager import is_empty_node, get_node_title, get_child_nodes, get_non_empty_sibling_nodes, get_parent_node, \
    get_node_content, get_node_image, get_node_hyperlink, XManager, NodeNotFoundError


def test_x_manager(x_manager):
    # given
    expected_sheets = ['biological psychology', 'clinical psychology', 'ref']
    expected_referenced_file = [cts.GENERAL_PSYCHOLOGY_MAP_PATH]
    # when
    cut = x_manager
    # then
    assert list(cut.sheets.keys()) == expected_sheets
    assert cut.referenced_files == expected_referenced_file


def test_x_manager_wrong_file_path():
    # when
    with pytest.raises(FileNotFoundError) as exception_info:
        XManager(file=cts.ABSENT_XMIND_FILE_PATH)
    # then
    assert exception_info.value.args[0] == XManager.FILE_NOT_FOUND_MESSAGE.format(cts.ABSENT_XMIND_FILE_PATH)


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


def test_get_tag_by_id_tag_not_found(x_manager):
    # given
    node_id = 'absent_id'
    # when
    with pytest.raises(NodeNotFoundError) as exception_info:
        x_manager.get_tag_by_id(node_id)
    # then
    assert exception_info.value.message == NodeNotFoundError.ERROR_MESSAGE.format(node_id)


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
    tag = x_manager.get_tag_by_id('23nu73chqkkkem455dit5p8stu')
    # when
    node_content = get_node_content(tag=tag)
    # then
    assert node_content == cts.MEDIA_ATTACHMENT_NODE_CONTENT


def test_get_node_content_with_media_via_hyperlink(x_manager):
    # given
    tag = x_manager.get_tag_by_id(cts.MEDIA_HYPERLINK_XMIND_ID)
    # when
    node_content = get_node_content(tag=tag)
    # then
    assert node_content == cts.MEDIA_HYPERLINK_NODE_CONTENT


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
    assert node_media == "file://C:/Users/lloos/OneDrive%20-%20bwedu/Projects/AnkiAddon/anki-addon-dev/addons21" \
                         "/XmindImport/resources/serotonin.mp3"


def test_extract_attachment(x_manager):
    # when
    attachment = x_manager.read_attachment("attachments/395ke7i9a6nkutu85fcpa66as2.mp4")
    # then
    assert type(attachment) == bytes


def test_get_map_last_modified(x_manager):
    # when
    map_last_modified = x_manager.get_map_last_modified()
    # then
    assert map_last_modified > 15956710897


def test_get_sheet_last_modified(x_manager):
    # when
    sheet_last_modified = x_manager.get_sheet_last_modified('biological psychology')
    # then
    assert sheet_last_modified > 15956710897
