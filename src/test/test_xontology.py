from main import xontology
import test.constants as cts


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
