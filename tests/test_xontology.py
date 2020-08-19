import pytest

import smr.xontology as xontology
import tests.constants as cts
from owlready2 import ThingClass, ObjectPropertyClass
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.xmindnodedto import XmindNodeDto


def test_xontology(x_ontology):
    # when
    cut = x_ontology
    # then
    cut._set_up_classes.assert_called()
    assert cut.field_translator is not None


def test_concept_from_node_content(x_ontology):
    # given
    cut = x_ontology
    id_1 = 'my_id'
    id_2 = 'my_other_id'
    # when
    concept = cut.concept_from_node_content(node_content=cts.NEUROTRANSMITTERS_NODE_CONTENT, node_id=id_1)
    # then
    assert isinstance(getattr(cut, cts.NEUROTRANSMITTERS_CLASS_NAME), cut.Concept)
    assert concept.XmindId[0] == id_1
    # when
    concept = cut.concept_from_node_content(node_content=cts.NEUROTRANSMITTERS_NODE_CONTENT, node_id=id_2)
    assert concept.XmindId == [id_1, id_2]


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


def test_connect_concepts(x_ontology):
    # given
    cut = x_ontology
    parent_concept = cut.Concept('parent')
    parent_2_concept = cut.Concept('parent2')
    child_1_concept = cut.Concept('child')
    child_2_concept = cut.Concept('child2')
    relationship_class_name = 'relationship'
    edge_id = 'some_edge_id'
    x_ontology.add_relation(relationship_class_name)
    # when
    cut.connect_concepts(parent_thing=parent_concept, relationship_class_name=relationship_class_name,
                         child_thing=child_1_concept, edge_id=edge_id)
    # then
    assert cut.parent.relationship == [child_1_concept]
    assert cut.child.Parent == [parent_concept]
    # when
    cut.connect_concepts(parent_thing=parent_concept, relationship_class_name=relationship_class_name,
                         child_thing=child_2_concept, edge_id=edge_id)
    # then
    assert cut.parent.relationship == [child_1_concept, child_2_concept]
    # when
    cut.connect_concepts(parent_thing=parent_2_concept, relationship_class_name=relationship_class_name,
                         child_thing=child_1_concept, edge_id=edge_id)
    # then
    assert cut.parent.relationship == [child_1_concept, child_2_concept]
    assert cut.child.Parent == [parent_concept, parent_2_concept]
    assert cut.XmindId[parent_concept, getattr(cut, relationship_class_name), child_1_concept][0] == edge_id
    assert cut.XmindId[parent_concept, getattr(cut, relationship_class_name), child_2_concept][0] == edge_id
    assert cut.XmindId[parent_2_concept, getattr(cut, relationship_class_name), child_1_concept][0] == edge_id


@pytest.fixture
def ontology_with_example_map(smr_world_with_example_map, collection_with_example_map) -> xontology.XOntology:
    yield xontology.XOntology(
        deck_id=collection_with_example_map.decks.id('testdeck', create=False), smr_world=smr_world_with_example_map)


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
                          edge_id=cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert [getattr(p, relation_name) for p in parents] == 4 * [[]]
    assert len(child.Parent) == 1


def test_change_relationship_class_name(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    parent_storids = [getattr(cut, i).storid for i in cts.MULTIPLE_PARENTS_CLASS_NAMES]
    relation_storid = getattr(cut, cts.MULTIPLE_PARENTS_RELATION_CLASS_NAME).storid
    child_storid = getattr(cut, cts.MULTIPLE_PARENTS_CHILD_CLASS_NAME).storid
    # when
    new_property = cut.change_relationship_class_name(
        parent_storids=parent_storids, relation_storid=relation_storid, child_storids=[child_storid],
        new_question_content=NodeContentDto(title='new question', image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI),
        edge_id=cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)
    # then
    assert new_property.name == 'new_questionximage_09r2e442o8lppjfeblf7il2rmd_extension_png_xrelation'


def test_remove_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    storid = cut.one_or_more_amine_groups.storid
    # when
    cut.remove_node(xmind_node=XmindNodeDto(ontology_storid=storid, node_id='0s0is5027b7r6akh3he0nbu478'),
                    xmind_edge=XmindNodeDto(), parent_concept_storids=[])
    # then
    assert not cut.one_or_more_amine_groups
    assert not cut.biogenic_amines.consist_of_xrelation


def test_remove_node_does_not_remove_concept_if_nodes_left(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    storid = cut.Serotonin.storid
    # when
    cut.remove_node(xmind_node=XmindNodeDto(ontology_storid=storid, node_id='3732cbg8qsmr8u4hn0bvljso06'),
                    xmind_edge=XmindNodeDto(title="can be inhibited by", node_id="1scualcvt0scjd9iaoblg568ld"),
                    parent_concept_storids=[cut.Pain.storid])
    # then
    assert type(cut.Serotonin) == cut.Concept
    assert not cut.Pain.can_be_inhibited_by_xrelation


