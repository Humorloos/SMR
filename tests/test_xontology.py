import pytest

import xontology
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
DECK_ID = "99999"


@pytest.fixture
def x_ontology(mocker, smr_world_for_tests):
    mocker.patch('xontology.mw')
    xontology.mw.smr_world = smr_world_for_tests
    mocker.spy(xontology.XOntology, "_set_up_classes")
    yield xontology.XOntology(DECK_ID)


def test_xontology(x_ontology):
    # when
    cut = x_ontology
    # then
    cut._set_up_classes.assert_called()
    assert cut.field_translator is not None
    assert list(cut.graph.execute(
        "SELECT * FROM ontology_lives_in_deck WHERE deck_id = {}".format(int(DECK_ID))).fetchall())[0] == (99999, 3)
