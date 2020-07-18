import pytest

import xontology
import XmindImport.tests.constants as cts

# class TestGetQuestion(TestXOntology):
#     def test_get_question(self):
#         x_id = '08eq1rdricsp1nt1b7aa181sq4'
#         act = self.x_ontology.get_question(x_id=x_id)
#         self.fail()
#
#     def test_two_answers(self):
#         x_id = ('4kdqkutdha46uns1j8jndi43ht')
#         act = self.x_ontology.get_question(x_id=x_id)
#         self.fail()
#
#
# class TestChangeQuestion(TestXOntology):
#     def test_change_question(self):
#         x_id = '08eq1rdricsp1nt1b7aa181sq4'
#         new_question = 'former image'
#         self.x_ontology.change_question(
#             x_id=x_id,
#             new_question=new_question)
#         act = self.x_ontology.get_question(x_id)[0]['p'].name
#         self.assertEqual('former_image', act)
#
#     def test_two_answers(self):
#         x_id = '4kdqkutdha46uns1j8jndi43ht'
#         self.x_ontology.change_question(x_id=x_id,
#                                         new_question='whatever')
#         act = self.x_ontology.get_question(x_id)[0]['p'].name
#         self.assertEqual('whatever', act)
#
#
# class TestGetNoteTriples(TestXOntology):
#     def test_get_note_triples(self):
#         a = self.x_ontology.getNoteTriples()
#         self.fail()


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
