import urllib

from smr.dto.topiccontentdto import TopicContentDto
from tests import constants as cts


def test_is_empty(xmind_node):
    # when
    empty = xmind_node.is_empty
    # then
    assert empty is False


def test_title(xmind_node):
    # when
    title = xmind_node.title
    # then
    assert title == 'biological psychology'


def test_content(xmind_node):
    # when
    node_content = xmind_node.content
    # then
    assert node_content.title == 'biological psychology'
    assert node_content.image is None
    assert node_content.media is None


def test_content_with_image(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    # when
    node_content = node.content
    # then
    assert node_content == cts.NEUROTRANSMITTERS_NODE_CONTENT


def test_content_with_media(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.DE_EMBEDDED_MEDIA_NODE_ID)
    # when
    node_content = node.content
    # then
    assert node_content == cts.MEDIA_ATTACHMENT_NODE_CONTENT


def test_content_with_media_via_hyperlink(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    # when
    node_content = node.content
    # then
    assert node_content == cts.MEDIA_HYPERLINK_NODE_CONTENT


def test_parent_edge(x_manager):
    # given
    expected_parent = "splits up"
    # when
    parent_edge = x_manager.get_node_by_id(cts.EMPTY_NODE_ID).parent_edge
    # then
    assert parent_edge.title == expected_parent


def test_non_empty_sibling_nodes(x_manager):
    # given
    expected_siblings = ['Serotonin', 'dopamine', 'adrenaline', 'noradrenaline']
    # when
    sibling_nodes = x_manager.get_node_by_id(cts.EMPTY_NODE_ID).non_empty_sibling_nodes
    # then
    assert [n.title for n in sibling_nodes] == expected_siblings


def test_image(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.NEUROTRANSMITTERS_NODE_ID)
    # when
    node_image = node.image
    # then
    assert node_image == 'attachments/629d18n2i73im903jkrjmr98fg.png'


def test_hyperlink(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    # when
    node_media = node.hyperlink
    # then
    assert urllib.parse.unquote(node_media[5:]) == cts.NAME_HYPERLINK_MEDIA


def test_media(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    # when
    node_media = node.media
    # then
    assert node_media == cts.PATH_HYPERLINK_MEDIA_TEMPORARY


def test_get_child_nodes(x_manager):
    # when
    child_nodes = x_manager.get_edge_by_id(cts.CONSIST_OF_EDGE_ID).child_nodes
    # then
    assert child_nodes[0].id == cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID


def test_title_setter(xmind_node):
    # given
    title = 'new title'
    # when
    xmind_node.title = title
    # then
    assert xmind_node.content == TopicContentDto(title=title)


def test_hyperlink_uri(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    # when
    uri = node.hyperlink_uri
    # then
    assert uri == cts.PATH_HYPERLINK_MEDIA_TEMPORARY


def test_get_hyperlink_uri_embedded_file(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.DE_EMBEDDED_MEDIA_NODE_ID)
    # when
    uri = node.hyperlink_uri
    # then
    assert uri == 'attachments/395ke7i9a6nkutu85fcpa66as2.mp4'


def test_get_reference(x_manager):
    # given
    edge = x_manager.get_edge_by_id(cts.TYPES_EDGE_ID)
    # when
    ref = edge.get_reference()
    # then
    assert ref == """\
biological psychology
investigates: information transfer and processing
requires: neurotransmitters (image)"""


def test_order_number(x_manager):
    # given
    node = x_manager.get_node_by_id(cts.EMPTY_NODE_ID)
    # then
    assert node.order_number == 5
