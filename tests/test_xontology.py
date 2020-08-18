import pytest

import smr.xontology as xontology
import tests.constants as cts
from owlready2 import ThingClass, ObjectPropertyClass
from smr.dto.nodecontentdto import NodeContentDto


def test_xontology(x_ontology):
    # when
    cut = x_ontology
    # then
    cut._set_up_classes.assert_called()
    assert cut.field_translator is not None


def test_add_concept(x_ontology):
    # given
    cut = x_ontology
    # when
    cut.concept_from_node_content(node_content=cts.NEUROTRANSMITTERS_NODE_CONTENT)
    # then
    assert isinstance(getattr(cut, cts.NEUROTRANSMITTERS_CLASS_NAME), cut.Concept)


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
    x_ontology.add_relation(relationship_class_name)
    # when
    xontology.connect_concepts(parent_thing=parent_concept, relationship_class_name=relationship_class_name,
                               child_thing=child_1_concept)
    # then
    assert cut.parent.relationship == [child_1_concept]
    assert cut.child.Parent == [parent_concept]
    # when
    xontology.connect_concepts(parent_thing=parent_concept, relationship_class_name=relationship_class_name,
                               child_thing=child_2_concept)
    # then
    assert cut.parent.relationship == [child_1_concept, child_2_concept]
    # when
    xontology.connect_concepts(parent_thing=parent_2_concept, relationship_class_name=relationship_class_name,
                               child_thing=child_1_concept)
    # then
    assert cut.parent.relationship == [child_1_concept, child_2_concept]
    assert cut.child.Parent == [parent_concept, parent_2_concept]


@pytest.fixture
def ontology_with_example_map(smr_world_with_example_map) -> xontology.XOntology:
    yield xontology.XOntology(deck_id=1597504882385, smr_world=smr_world_with_example_map)


def test_get_concept(ontology_with_example_map):
    # when
    concept = ontology_with_example_map.get(cts.MULTIPLE_PARENTS_CHILD_STORID)
    # then
    assert isinstance(concept, ontology_with_example_map.Concept)


def test_get_relationship_property(ontology_with_example_map):
    # when
    concept = ontology_with_example_map.get(cts.MULTIPLE_PARENTS_RELATION_STORID)
    # then
    assert isinstance(concept, ObjectPropertyClass)


def test_remove_relations(ontology_with_example_map):
    # given
    onto = ontology_with_example_map
    child = onto.get(cts.MULTIPLE_PARENTS_CHILD_STORID)
    parents = {onto.get(i) for i in cts.MULTIPLE_PARENTS_STORIDS}
    relation_name = onto.get(cts.MULTIPLE_PARENTS_RELATION_STORID).name
    # when
    xontology.remove_relations(children={child}, parents=parents, relation_name=relation_name)
    # then
    assert [getattr(p, relation_name) for p in parents] == 4 * [[]]
    assert len(child.Parent) == 1


def test_change_relationship_class_name(ontology_with_example_map):
    # when
    new_property = ontology_with_example_map.change_relationship_class_name(
        parent_storids=cts.MULTIPLE_PARENTS_STORIDS, relation_storid=cts.MULTIPLE_PARENTS_RELATION_STORID,
        child_storids=[cts.MULTIPLE_PARENTS_CHILD_STORID],
        new_question_content=NodeContentDto(title='new question', image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI))
    # then
    assert new_property.name == 'new_question_ximage_09r2e442o8lppjfeblf7il2rmd_extension_png_xrelation'
