from assertpy import assert_that

import tests.constants as cts
from owlready2 import ObjectPropertyClass, ObjectProperty
from smr.dto.topiccontentdto import TopicContentDto
from smr.dto.xmindtopicdto import XmindTopicDto
from smr.fieldtranslator import PARENT_RELATION_NAME, relation_class_from_content, CHILD_RELATION_NAME


def test_xontology(x_ontology):
    # when
    cut = x_ontology
    # then
    cut._set_up_classes.assert_called()


def test_add_concept_from_node(ontology_with_example_map, x_manager):
    # given
    cut = ontology_with_example_map
    node_1 = XmindTopicDto(node_id='node_1', sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID, title='node',
                           order_number=1)
    # when
    cut.add_concepts_from_nodes([node_1])
    # then
    concept = getattr(cut, node_1.title)
    assert isinstance(concept, cut.Concept)
    assert cut.get_concept_from_node_id(node_1.node_id) == concept


def test_add_relations_from_edges(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    edge_class_name = 'edge_xrelation'
    edge = XmindTopicDto(node_id='edge_id', title='edge', sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # then
    assert getattr(cut, edge_class_name) is None
    # when
    cut.add_relations_from_edges([edge])
    # then
    relation = getattr(cut, edge_class_name)
    assert relation.name == edge_class_name
    assert cut.get_relation_from_edge_id('edge_id') == relation


def test_connect_concepts(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    relationship_class_name = 'relationship_xrelation'
    edge_id = 'some_edge_id'
    cut.add_relations_from_edges([XmindTopicDto(node_id=edge_id, title='relationship',
                                                sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)])
    child_1 = cut.get_concept_from_node_id(cts.DE_EMBEDDED_MEDIA_NODE_ID)
    child_2 = cut.get_concept_from_node_id(cts.PAIN_1_NODE_ID)
    parent_1 = cut.get_concept_from_node_id(cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID)
    parent_2 = cut.get_concept_from_node_id(cts.BIOLOGICAL_PSYCHOLOGY_NODE_ID)
    relation = cut.get_relation_from_edge_id(edge_id)
    # when
    cut.connect_concepts(parent_storid=parent_1.storid, relation_class_name=relationship_class_name,
                         child_storid=child_1.storid)
    # then
    assert parent_1.relationship_xrelation == [child_1]
    assert parent_1 in getattr(child_1, PARENT_RELATION_NAME)
    # when
    cut.connect_concepts(parent_storid=parent_1.storid, relation_storid=relation.storid, child_storid=child_2.storid)
    # then
    assert parent_1.relationship_xrelation == [child_1, child_2]
    # when
    cut.connect_concepts(parent_storid=parent_2.storid, relation_class_name=relationship_class_name,
                         child_storid=child_1.storid)
    # then
    assert parent_1.relationship_xrelation == [child_1, child_2]
    assert_that(getattr(child_1, PARENT_RELATION_NAME)).contains(parent_1, parent_2)


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


def test_rename_relation(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.rename_relation(
        XmindTopicDto(node_id=cts.ARE_EDGE_ID, title='new question', image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI))
    # then
    new_property = cut.get_relation_from_edge_id(cts.ARE_EDGE_ID)
    assert new_property.name == 'new_questionximage_09r2e442o8lppjfeblf7il2rmd_extension_png_xrelation'


def test_rename_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    node = XmindTopicDto(node_id=cts.BIOGENIC_AMINES_2_NODE_ID, title='nothing',
                         image=cts.NEUROTRANSMITTERS_IMAGE_XMIND_URI, sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # when
    cut.rename_node(xmind_node=node)
    # then
    new_concept = cut.get_concept_from_node_id(cts.BIOGENIC_AMINES_2_NODE_ID)
    assert getattr(new_concept, PARENT_RELATION_NAME) == [getattr(cut, n) for n in cts.MULTIPLE_PARENTS_CLASS_NAMES]
    assert len(new_concept.consist_of_xrelation) == 1
    assert new_concept in getattr(cut.one_or_more_amine_groups, PARENT_RELATION_NAME)


def test_rename_node_where_node_is_only_node_of_concept(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    node = XmindTopicDto(node_id=cts.NOCICEPTORS_NODE_ID, title='nothing', sheet_id=cts.BIOLOGICAL_PSYCHOLOGY_SHEET_ID)
    # when
    cut.rename_node(xmind_node=node)
    # then
    new_concept = cut.get_concept_from_node_id(cts.NOCICEPTORS_NODE_ID)
    assert getattr(new_concept, PARENT_RELATION_NAME) == [cut.Pain]
    assert len(new_concept.can_be_xrelation) == 1
    assert new_concept in getattr(cut.chemical, PARENT_RELATION_NAME)


def test_get_concept_from_node_id(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # then
    assert cut.get_concept_from_node_id('122vli15fp65smkg4v6pq54gi3') == cut.Serotonin


def test_get_relation_from_edge_id(ontology_with_example_map):
    assert ontology_with_example_map.get_relation_from_edge_id(cts.TYPES_EDGE_ID) == \
           ontology_with_example_map.types_xrelation


def test_move_edges(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.move_edges({cts.AFFECTS_EDGE_ID: set(cts.MULTIPLE_PARENTS_NODE_IDS),
                    cts.CONSIST_OF_EDGE_ID: {cts.SEROTONIN_MEDIA_HYPERLINK_NODE_ID},
                    cts.SPLITS_UP_EDGE_ID: {cts.BIOGENIC_AMINES_1_NODE_ID}})
    # then
    references = cut.world.get_smr_note_reference_fields([cts.AFFECTS_EDGE_ID, cts.CONSIST_OF_EDGE_ID])
    assert_that(references.values()).contains(
        'biological psychology<li>investigates: information transfer and processing</li><li>requires: '
        'neurotransmitters<br><img src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic '
        'amines</li><li>splits up: Serotonin, dopamine, adrenaline, noradrenaline</li>',
        'biological psychology<li>investigates: information transfer and processing</li><li>requires: '
        'neurotransmitters<br><img src="attachments629d18n2i73im903jkrjmr98fg.png"></li><li>types: biogenic '
        'amines</li><li><img src="attachments09r2e442o8lppjfeblf7il2rmd.png">: Serotonin</li><li>pronounciation: ('
        'media)</li>'
    )
    assert cut.get_concept_from_node_id(cts.MAO_2_NODE_ID).splits_up_xrelation == []
    assert_that(cut.biogenic_amines.splits_up_xrelation).contains(*[
        cut.get_concept_from_node_id(i) for i in cts.MULTIPLE_PARENTS_NODE_IDS])


def test_move_nodes(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.move_nodes({cts.MODULATED_BY_EDGE_ID: cts.PERCEPTION_NODE_ID,
                    cts.EMPTY_EDGE_3_ID: cts.SLEEP_NODE_ID,
                    cts.AFFECTS_EDGE_ID: cts.NORADRENALINE_NODE_ID})
    # then
    assert_that(cut.get_concept_from_node_id(cts.MAO_2_NODE_ID).splits_up_xrelation) \
        .contains(cut.Serotonin, cut.adrenaline, cut.dopamine) \
        .does_not_contain(cut.noradrenaline)
    assert_that(cut.get_concept_from_node_id(cts.SEROTONIN_1_NODE_ID).affects_xrelation).contains(cut.noradrenaline)
    assert cut.world.get_smr_note_reference_fields([cts.EMPTY_EDGE_3_ID])[
               cts.EMPTY_EDGE_3_ID] == 'biological psychology<li>investigates: information transfer and ' \
                                       'processing</li><li>modulated by: perception</li>'


def test_disconnect_node(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.disconnect_node(cts.SEROTONIN_1_NODE_ID)
    # then
    serotonin = cut.Serotonin
    # node's parent relation to "biogenic amines" must be removed
    assert len(serotonin.smrparent_xrelation) == 5
    # node's child relation to "MAO" must not be removed since there is another case of this type of relation in the map
    assert len(getattr(serotonin, CHILD_RELATION_NAME)) == 1
    # node's child relation affects relations must be removed
    assert len(serotonin.affects_xrelation) == 0
    # child node's parent relation must be removed
    assert serotonin not in cut.Pain.smrparent_xrelation
    # parent node's child relation must be removed
    assert len(getattr(cut.biogenic_amines,
                       relation_class_from_content(TopicContentDto(image=cts.EXAMPLE_IMAGE_ATTACHMENT_NAME)))) == 0


def test_disconnect_edge(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.disconnect_edge(cts.ARE_EDGE_ID)
    # then
    # relationship property must be removed
    assert cut.are_xrelation is None


def test_disconnect_edge_remove_objs_triples(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.disconnect_edge(cts.EMPTY_EDGE_3_ID)
    # then
    # relationship property must not be removed if other instance is left
    assert isinstance(getattr(cut, CHILD_RELATION_NAME), ObjectProperty.__class__)
    # edge's child relation must be removed
    assert not getattr(cut.perception, CHILD_RELATION_NAME)
    # edge's parent relation must be removed
    assert cut.perception not in getattr(cut.Pain, PARENT_RELATION_NAME)


def test_remove_xmind_edges(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.remove_xmind_edges({cts.EXAMPLE_IMAGE_EDGE_ID, cts.ARE_EDGE_ID})
    # then
    assert_that([r.edge_id for r in cut.world._get_records("select * from main.xmind_edges")]).does_not_contain(
        cts.ARE_EDGE_ID, cts.EXAMPLE_IMAGE_EDGE_ID)
    assert_that([r.edge_id for r in cut.world._get_records("select * from main.smr_triples")]).does_not_contain(
        cts.ARE_EDGE_ID, cts.EXAMPLE_IMAGE_EDGE_ID)
    assert_that([r.edge_id for r in cut.world._get_records("select * from main.smr_notes")]).does_not_contain(
        cts.ARE_EDGE_ID, cts.EXAMPLE_IMAGE_EDGE_ID)
    assert not cut.are_xrelation


def test_remove_xmind_edges_foreign_key_cascade(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    edges_2_remove = {cts.EMPTY_EDGE_2_NODE_ID, cts.MEANS_IN_ENGLISH_EDGE_ID, cts.STANDS_FOR_EDGE_ID,
                      '0eaob1gla0j1qriki94n2os9oe', '61irckf1nloq42brfmbu0ke92v', '7e1s0urn8376a2q371nujihuab',
                      '32dt8d2dflh4lr5oqc2oqqad28', '6iivm8tpoqj2c0euaabtput14l'}
    # when
    cut.remove_xmind_edges(edges_2_remove)
    # then
    # smr notes must be removed
    assert len(cut.world._get_records(
        f"""select * from main.smr_notes where edge_id IN ('{"', '".join(edges_2_remove)}')""")) == 0
    # smr triples must be removed
    assert len(cut.world._get_records(
        f"""select * from main.smr_triples where edge_id IN ('{"', '".join(edges_2_remove)}')""")) == 0
    # edge's relations must not be removed if there is a copy still existing in the map
    assert getattr(cut.Serotonin, CHILD_RELATION_NAME) == [cut.MAO]
    assert cut.Serotonin in getattr(cut.MAO, PARENT_RELATION_NAME)
    # edge's relations must be removed if there are no copies remaining
    assert cut.MAO.stands_for_xrelation == []
    assert getattr(cut.monoamine_oxidase, PARENT_RELATION_NAME) == []


def test_remove_xmind_nodes(ontology_with_example_map):
    # given
    cut = ontology_with_example_map
    # when
    cut.remove_xmind_nodes([cts.NEUROTRANSMITTERS_NODE_ID, cts.MAO_2_NODE_ID, cts.NOCICEPTORS_NODE_ID,
                            cts.MAO_1_NODE_ID])
    # then
    remaining_node_ids = [e[0] for e in cut.graph.execute("select node_id from xmind_nodes").fetchall()]
    assert cts.NEUROTRANSMITTERS_NODE_ID not in remaining_node_ids
    assert cts.MAO_2_NODE_ID not in remaining_node_ids
    # triples must be removed
    assert cut.world._get_records(f"""
select * from main.smr_triples where parent_node_id = '{cts.MAO_2_NODE_ID}'""") == []
    # ontology:
    mao = cut.MAO
    # node's child relation that is still present at different location must not be removed
    assert len(mao.difference_xrelation) == 1
    # node's child relation that was only part of the deleted node must be removed
    assert len(mao.types_in_humans_xrelation) == 0
    # node's parent relation must be removed
    assert_that(mao.smrparent_xrelation).does_not_contain(cut.enzymes)
    # parent node's child relation must be removed
    assert len(cut.Pain.triggered_by_xrelation) == 0
    # child node's parent relation must be removed
    assert len(cut.chemical.smrparent_xrelation) == 0
