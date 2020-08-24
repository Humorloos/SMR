import urllib

import bs4
import pytest

import tests.constants as cts
from smr.dto.nodecontentdto import NodeContentDto
from smr.xmanager import is_empty_node, get_node_title, get_non_empty_sibling_nodes, get_parent_node, \
    get_node_image, get_node_hyperlink, XManager, NodeNotFoundError
from smr.xmindsheet import get_root_node, get_child_nodes


def test_x_manager(x_manager):
    # given
    expected_sheets = [cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID, '1bt0u8ahp0p8d41j6pto2d9q8t']
    # when
    cut = x_manager
    # then
    assert list(cut.sheets.keys()) == expected_sheets


def test_x_manager_wrong_file_path():
    # given
    cut = XManager(file=cts.ABSENT_XMIND_FILE_PATH)
    # when
    with pytest.raises(FileNotFoundError) as exception_info:
        assert cut.soup
    # then
    assert exception_info.value.args[1] == 'No such file or directory'


def test_get_root_node(x_manager):
    # given
    cut = x_manager
    # when
    root_node = get_root_node(cut.sheets, sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert get_node_title(root_node) == 'biological psychology'


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


def test_get_tag_by_id(x_manager):
    # when
    tag = x_manager.get_tag_by_id(cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID)
    # then
    assert tag.text == 'one or more amine groups'


def test_get_tag_by_id_tag_not_found(x_manager):
    # given
    node_id = 'absent_id'
    # when
    with pytest.raises(NodeNotFoundError) as exception_info:
        x_manager.get_tag_by_id(node_id)
    # then
    assert exception_info.value.message == NodeNotFoundError.ERROR_MESSAGE.format(node_id)


def test_get_node_content(x_manager, tag_for_tests):
    # when
    node_content = x_manager.get_node_content(tag=tag_for_tests)
    # then
    assert node_content.title == 'biological psychology'
    assert node_content.image is None
    assert node_content.media is None


def test_get_node_content_with_image(x_manager):
    # given
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    # when
    node_content = x_manager.get_node_content(tag=tag)
    # then
    assert node_content == cts.NEUROTRANSMITTERS_NODE_CONTENT


def test_get_node_content_with_media(x_manager):
    # given
    tag = x_manager.get_tag_by_id('23nu73chqkkkem455dit5p8stu')
    # when
    node_content = x_manager.get_node_content(tag=tag)
    # then
    assert node_content == cts.MEDIA_ATTACHMENT_NODE_CONTENT


def test_get_node_content_with_media_via_hyperlink(x_manager):
    # given
    tag = x_manager.get_tag_by_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    # when
    node_content = x_manager.get_node_content(tag=tag)
    # then
    assert node_content == cts.MEDIA_HYPERLINK_NODE_CONTENT


def test_get_sheet_name(x_manager):
    # when
    sheet_id = x_manager.get_sheet_name(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert sheet_id == 'biological psychology'


def test_get_child_nodes(x_manager):
    # when
    child_nodes = get_child_nodes(x_manager.get_tag_by_id(cts.CONSIST_OF_EDGE_ID))
    # then
    assert child_nodes[0]['id'] == cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID


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
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
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
    assert urllib.parse.unquote(node_media[5:]) == cts.NAME_HYPERLINK_MEDIA


def test_extract_attachment(x_manager):
    # when
    attachment = x_manager.read_attachment("attachments/395ke7i9a6nkutu85fcpa66as2.mp4")
    # then
    assert type(attachment) == bytes


def test_map_last_modified(x_manager):
    # when
    map_last_modified = x_manager.map_last_modified
    # then
    assert map_last_modified > 15956710897


def test_get_sheet_last_modified(x_manager):
    # when
    sheet_last_modified = x_manager.get_sheet_last_modified(cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert sheet_last_modified > 15956710897


def test_set_node_title(x_manager, tag_for_tests):
    # given
    title = 'new title'
    # when
    x_manager.set_node_title(tag_for_tests, title)
    # then
    assert get_node_title(tag_for_tests) == title


def test_set_node_image_remove(x_manager, changed_collection_with_example_map, smr_world_with_example_map):
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    node_image = get_node_image(tag)
    # when
    x_manager.set_node_image(tag=tag, note_image=None, node_image=node_image,
                             media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
                             smr_world=smr_world_with_example_map)
    # then
    assert get_node_image(tag) is None
    with pytest.raises(TypeError) as error_info:
        smr_world_with_example_map.get_anki_file_name_from_xmind_uri(node_image[4:])
    assert error_info.value.args[0] == '\'NoneType\' object is not subscriptable'
    assert x_manager.did_introduce_changes is True
    assert x_manager.file_bin[0] == node_image[4:]


def test_set_node_image_add(x_manager, changed_collection_with_example_map, smr_world_with_example_map, tag_for_tests):
    tag = tag_for_tests
    expected_image = 'xap:paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg'
    # when
    x_manager.set_node_image(tag=tag, note_image=cts.NEW_IMAGE_NAME, node_image=None,
                             media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
                             smr_world=smr_world_with_example_map)
    # then
    assert get_node_image(tag) == expected_image
    assert smr_world_with_example_map.get_anki_file_name_from_xmind_uri(expected_image[4:]) == expected_image[4:]
    assert x_manager.did_introduce_changes is True
    assert len(x_manager.file_bin) == 0


def test_set_node_image_change(x_manager, changed_collection_with_example_map, smr_world_with_example_map,
                               tag_for_tests):
    tag = x_manager.get_tag_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    expected_image = 'xap:paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg'
    old_image = get_node_image(tag)
    # when
    x_manager.set_node_image(tag=tag, note_image=cts.NEW_IMAGE_NAME, node_image=old_image,
                             media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA,
                             smr_world=smr_world_with_example_map)
    # then
    assert get_node_image(tag) == expected_image
    assert smr_world_with_example_map.get_anki_file_name_from_xmind_uri(expected_image[4:]) == expected_image[4:]
    assert x_manager.did_introduce_changes is True
    assert x_manager.file_bin[0] == old_image[4:]


def test_remove_node(x_manager):
    # given
    node_id = '3nb97928e68dcu5512pft7gkcg'
    # when
    x_manager.remove_node(node_id)
    # then
    with pytest.raises(NodeNotFoundError):
        x_manager.get_tag_by_id(node_id)


def test_remove_node_invalid_removal(x_manager):
    # when
    with pytest.raises(AttributeError) as error_info:
        x_manager.remove_node(cts.NEUROTRANSMITTERS_NODE_ID)
    # then
    assert error_info.value.args[0] == 'Topic has subtopics, can not remove.'


def test_get_hyperlink_uri(x_manager):
    # given
    cut = x_manager
    tag = x_manager.get_tag_by_id("1s7h0rvsclrnvs8qq9u71acml5")
    # when
    uri = cut.get_hyperlink_uri(tag)
    # then
    assert uri == cts.PATH_HYPERLINK_MEDIA_TEMPORARY


def test_get_hyperlink_uri_embedded_file(x_manager):
    # given
    cut = x_manager
    tag = x_manager.get_tag_by_id("23nu73chqkkkem455dit5p8stu")
    # when
    uri = cut.get_hyperlink_uri(tag)
    # then
    assert uri == 'attachments/395ke7i9a6nkutu85fcpa66as2.mp4'


def test_save_changes(x_manager, smr_world_with_example_map):
    # given
    new_node_content = NodeContentDto(image=cts.NEW_IMAGE_NAME, title='new node title')
    x_manager.set_node_content(node_id=cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID, content=new_node_content,
                               media_directory=cts.TEST_COLLECTIONS_DIRECTORY, smr_world=smr_world_with_example_map)
    # when
    x_manager.save_changes()
    # then
    assert XManager(cts.PATH_EXAMPLE_MAP_TEMPORARY).get_node_content_by_id(
        cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID) == new_node_content


def test_set_node_content(x_manager, smr_world_with_example_map):
    # given
    new_node_content = NodeContentDto(image=cts.NEW_IMAGE_NAME, title='new node title')
    # when
    x_manager.set_node_content(node_id=cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID, content=new_node_content,
                               media_directory=cts.TEST_COLLECTIONS_DIRECTORY, smr_world=smr_world_with_example_map)
    # then
    assert smr_world_with_example_map.get_xmind_uri_from_anki_file_name(cts.NEW_IMAGE_NAME) == cts.NEW_IMAGE_NAME
    assert x_manager.get_node_content_by_id(cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID) == new_node_content
