import pytest

from smr.dto.topiccontentdto import TopicContentDto
from smr.xmanager import XManager, TopicNotFoundError
from tests import constants as cts


def test_x_manager(x_manager):
    # given
    expected_sheets = [cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID, cts.CLINICAL_PSYCHOLOGY_SHEET_ID]
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


def test_read_attachment(x_manager):
    # when
    attachment = x_manager.read_attachment("attachments/395ke7i9a6nkutu85fcpa66as2.mp4")
    # then
    assert type(attachment) == bytes


def test_set_topic_image_remove(x_manager, changed_collection_with_example_map):
    node = x_manager.get_node_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    old_image = node.image
    # when
    x_manager.set_topic_image(topic=node, image_name=None,
                              media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    # then
    assert node.image is None
    assert x_manager.did_introduce_changes is True
    assert x_manager.file_bin[0] == old_image


def test_set_topic_image_add(x_manager, changed_collection_with_example_map, tag_for_tests, xmind_node):
    expected_image = cts.NEW_IMAGE_NAME
    # when
    x_manager.set_topic_image(topic=xmind_node, image_name=cts.NEW_IMAGE_NAME,
                              media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    # then
    assert xmind_node.image == expected_image
    assert x_manager.did_introduce_changes is True
    assert len(x_manager.file_bin) == 0


def test_set_node_image_change(x_manager):
    node = x_manager.get_node_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    expected_image = cts.NEW_IMAGE_NAME
    old_image = node.image
    # when
    x_manager.set_topic_image(topic=node, image_name=cts.NEW_IMAGE_NAME,
                              media_directory=cts.TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    # then
    assert node.image == expected_image
    assert x_manager.did_introduce_changes is True
    assert x_manager.file_bin[0] == old_image


def test_remove_node(x_manager):
    # given
    node_id = cts.PAIN_1_NODE_ID
    # when
    x_manager.remove_node(node_id)
    # then
    with pytest.raises(TopicNotFoundError):
        x_manager.get_node_by_id(node_id)


def test_remove_node_invalid_removal(x_manager):
    # when
    with pytest.raises(AttributeError) as error_info:
        x_manager.remove_node(cts.NEUROTRANSMITTERS_NODE_ID)
    # then
    assert error_info.value.args[0] == 'Topic has subtopics, can not remove.'


def test_save_changes(x_manager):
    # given
    new_node_content = TopicContentDto(image=cts.NEW_IMAGE_NAME, title='new node title')
    x_manager.set_node_content(node_id=cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID, content=new_node_content,
                               media_directory=cts.TEST_COLLECTIONS_DIRECTORY)
    # when
    x_manager.save_changes()
    # then
    assert XManager(cts.PATH_EXAMPLE_MAP_TEMPORARY).get_node_content_by_id(
        cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID) == new_node_content


def test_set_node_content(x_manager):
    # given
    new_node_content = TopicContentDto(image=cts.NEW_IMAGE_NAME, title='new node title')
    # when
    x_manager.set_node_content(node_id=cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID, content=new_node_content,
                               media_directory=cts.TEST_COLLECTIONS_DIRECTORY)
    # then
    assert x_manager.get_node_content_by_id(cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID) == new_node_content


def test_get_node_by_id(x_manager):
    # when
    node = x_manager.get_node_by_id(cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID)
    # then
    assert node.title == 'one or more amine groups'


def test_get_tag_by_id_tag_not_found(x_manager):
    # given
    node_id = 'absent_id'
    # when
    with pytest.raises(TopicNotFoundError) as exception_info:
        x_manager.get_node_by_id(node_id)
    # then
    assert exception_info.value.message == TopicNotFoundError.ERROR_MESSAGE.format(node_id)


def test_map_last_modified(x_manager):
    # when
    map_last_modified = x_manager.map_last_modified
    # then
    assert map_last_modified > 15956710897