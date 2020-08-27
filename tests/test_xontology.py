import tests.constants as cts
from owlready2 import ObjectPropertyClass
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindtopicdto import XmindTopicDto


def test_xontology(x_ontology):
    # when
    cut = x_ontology
    # then
    cut._set_up_classes.assert_called()
    assert cut.field_translator is not None


def test_add_concept_from_node(x_ontology, x_manager):
    # given
    cut = x_ontology
    node_1 = x_manager.get_node_by_id(cts.PAIN_1_NODE_ID)
    node_2 = x_manager.get_node_by_id(cts.PAIN_2_NODE_ID)
    # when
    cut.add_concept_from_node(node_1.dto)
    # then
    assert isinstance(getattr(cut, node_1.title), cut.Concept)
    assert getattr(cut, node_1.title).XmindId[0] == node_1.id
    # when
    cut.add_concept_from_node(node_2.dto)
    assert getattr(cut, node_1.title).XmindId == [node_1.id, node_2.id]


def test_add_relation(x_ontology):
    # given
    cut = x_ontology
    relation_name = "new_relation"
    # then
    assert getattr(cut, relation_name) is None
    # when
    cut.add_relation(relation_name)
    # then
    assert getattr(cut, relation_name).name == relation_name


def test_connect_concepts(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    relationship_class_name = 'relationship'
    edge_id = 'some_edge_id'
    cut.add_relation(relationship_class_name)
    child_1 = cut.get_concept_from_node_id(cts.DE_EMBEDDED_MEDIA_NODE_ID)
    child_2 = cut.get_concept_from_node_id(cts.PAIN_1_NODE_ID)
    parent_1 = cut.get_concept_from_node_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    parent_2 = cut.get_concept_from_node_id(cts.BIOLOGICAL_PSYCHOLOGY_NODE_ID)
    # when
    cut.connect_concepts(parent_node_id=cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID,
                         relationship_class_name=relationship_class_name,
                         child_node_id=cts.DE_EMBEDDED_MEDIA_NODE_ID, edge_id=edge_id)
    # then
    assert parent_1.relationship == [child_1]
    assert parent_1 in getattr(child_1, cut.smr_world.parent_relation_name)
    # when
    cut.connect_concepts(parent_node_id=cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID,
                         relationship_class_name=relationship_class_name,
                         child_node_id=cts.PAIN_1_NODE_ID, edge_id=edge_id)
    # then
    assert parent_1.relationship == [child_1, child_2]
    # when
    cut.connect_concepts(parent_node_id=cts.BIOLOGICAL_PSYCHOLOGY_NODE_ID,
                         relationship_class_name=relationship_class_name,
                         child_node_id=cts.DE_EMBEDDED_MEDIA_NODE_ID, edge_id=edge_id)
    # then
    assert parent_1.relationship == [child_1, child_2]
    assert {parent_1, parent_2}.issubset({*getattr(child_1, cut.smr_world.parent_relation_name)})

    assert cut.XmindId[parent_1, getattr(cut, relationship_class_name), child_1][0] == edge_id
    assert cut.XmindId[parent_1, getattr(cut, relationship_class_name), child_2][0] == edge_id
    assert cut.XmindId[parent_2, getattr(cut, relationship_class_name), child_1][0] == edge_id


def test_get_concept(ontology_with_example_map):
    storid = getattr(ontology_with_example_map, cts.MULTIPLE_PARENTS_CHILD_CLASS_NAME).storid
    # when
    concept = ontology_with_example_map.get(storid)
    # then
    assert isinstance(concept, ontology_with_example_map.Concept)


def test_get_relationship_property(ontology_with_example_map):
    storid = getattr(ontology_with_example_map, cts.MULTIPLE_PARENTS_RELATION_CLASS_NAME).storid
    # when
    concept = ontology_with_example_map.get(storid)
    # then
    assert isinstance(concept, ObjectPropertyClass)


def test_remove_relations(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    child = getattr(onto, cts.MULTIPLE_PARENTS_CHILD_CLASS_NAME)
    parents = [getattr(onto, i) for i in cts.MULTIPLE_PARENTS_CLASS_NAMES]
    relation_name = cts.MULTIPLE_PARENTS_RELATION_CLASS_NAME
    # when
    onto.remove_relations(children=[child], parents=parents, relation_name=relation_name,
                          edge_id=cts.ARE_EDGE_ID)
    # then
    assert [getattr(p, relation_name) for p in parents] == 4 * [[]]
    assert len(getattr(child, onto.smr_world.parent_relation_name)) == 1


def test_change_relationship_class_name(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    parent_node_ids = cts.MULTIPLE_PARENTS_NODE_IDS
    child_node_id = cts.MULTIPLE_PARENTS_CHILD_NODE_ID
    # when
    new_property = cut.change_relationship_class_name(
        parent_node_ids=parent_node_ids, child_node_ids=[child_node_id],
        new_question_content=TopicContentDto(title='new question', image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI),
        edge_id=cts.ARE_EDGE_ID)
    # then
    assert new_property.name == 'new_questionximage_09r2e442o8lppjfeblf7il2rmd_extension_png_xrelation'


def test_remove_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.remove_node(xmind_node=XmindTopicDto(node_id=cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID),
                    xmind_edge=XmindTopicDto(), parent_node_ids=[], children={})
    # then
    assert not cut.one_or_more_amine_groups
    assert not cut.biogenic_amines.consist_of_xrelation


def test_remove_node_does_not_remove_concept_if_nodes_left(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    cut.nociceptors.XmindId.append('new_id')
    # when
    cut.remove_node(
        xmind_node=XmindTopicDto(node_id='2mbb2crv3tdgr131i9j538n0ga'),
        xmind_edge=XmindTopicDto(title="triggered by", node_id="4rdraflh6n2hl4a459g2urdkr6"),
        parent_node_ids=["5asru7kdmre8059cemi8p5lm3v"],
        children={'4q3e21ritrvitgmjialvadn2m6': ['2jf5kkori2h7sdja7cgje5i71e']})
    # then
    assert type(cut.nociceptors) == cut.Concept
    assert not cut.nociceptors.can_be_xrelation
    assert not getattr(cut.chemical, cut.smr_world.parent_relation_name)


def test_add_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.add_node(parent_edge=XmindTopicDto(node_id="1scualcvt0scjd9iaoblg568ld"),
                 relationship_class_name='can_be_inhibited_by_xrelation',
                 node_2_add=XmindTopicDto(node_id='some id', title='some title', image='abcde.png', link='fghij.mp3'),
                 parent_node_ids=['5asru7kdmre8059cemi8p5lm3v'])
    # then
    assert [c.name for c in cut.Pain.can_be_inhibited_by_xrelation] == [
        'Serotonin', 'some_titleximage_abcde_extension_pngxmedia_fghij_extension_mp3']


def test_rename_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.rename_node(xmind_edge=XmindTopicDto(
        title='are', node_id=cts.ARE_EDGE_ID), xmind_node=XmindTopicDto(
        node_id=cts.BIOGENIC_AMINES_NODE_ID, title='nothing', image='abcde.png', link='fghij.mp3'),
        parent_node_ids=cts.MULTIPLE_PARENTS_NODE_IDS,
        children={cts.CONSIST_OF_EDGE_ID: [cts.ONE_OR_MORE_AMINE_GROUPS_NODE_ID]})
    # then
    new_concept = cut.get_concept_from_node_id(cts.BIOGENIC_AMINES_NODE_ID)
    assert getattr(new_concept, cut.smr_world.parent_relation_name) == [
        getattr(cut, n) for n in cts.MULTIPLE_PARENTS_CLASS_NAMES]
    assert len(new_concept.consist_of_xrelation)
    assert new_concept in getattr(cut.one_or_more_amine_groups, cut.smr_world.parent_relation_name)


def test_get_concept_from_node_id(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # then
    assert cut.get_concept_from_node_id('122vli15fp65smkg4v6pq54gi3') == cut.Serotonin


def test_get_relation_from_edge_id(ontology_with_example_map):
    assert ontology_with_example_map.get_relation_from_edge_id(cts.TYPES_EDGE_ID) == \
           ontology_with_example_map.types_xrelation


def test_remove_sheet(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.remove_sheet(sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID, root_node_id=cts.BIOLOGICAL_PSYCHOLOGY_NODE_ID)
    # then
    assert not cut.Pain
    assert not cut.information_transfer_and_processing
    assert not cut.chemical
    assert not cut.Serotonin.pronounciation_xrelation
