from unittest import TestCase

from XmindImport.xontology import *
from XmindImport.consts import ADDON_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestXOntology(TestCase):
    def setUp(self):
        onto_path = os.path.join(SUPPORT_PATH,
                                 'ontology_biological_psychology.rdf')
        self.x_ontology = XOntology(onto_path)


class TestGetQuestion(TestXOntology):
    def test_get_question(self):
        x_id = '08eq1rdricsp1nt1b7aa181sq4'
        act = self.x_ontology.get_question(x_id=x_id)
        self.fail()

    def test_two_answers(self):
        x_id = ('4kdqkutdha46uns1j8jndi43ht')
        act = self.x_ontology.get_question(x_id=x_id)
        self.fail()


class TestChangeQuestion(TestXOntology):
    def test_change_question(self):
        x_id = '08eq1rdricsp1nt1b7aa181sq4'
        new_question = 'former image'
        self.x_ontology.change_question(
            x_id=x_id,
            new_question=new_question)
        act = self.x_ontology.get_question(x_id)[0]['p'].name
        self.assertEqual('former_image', act)

    def test_two_answers(self):
        x_id = '4kdqkutdha46uns1j8jndi43ht'
        self.x_ontology.change_question(x_id=x_id,
                                        new_question='whatever')
        act = self.x_ontology.get_question(x_id)[0]['p'].name
        self.assertEqual('whatever', act)


class TestGetNoteTriples(TestXOntology):
    def test_get_note_triples(self):
        a = self.x_ontology.getNoteTriples()
        self.fail()
