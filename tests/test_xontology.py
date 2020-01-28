from unittest import TestCase

from XmindImport.xontology import *
from XmindImport.consts import ADDON_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')

class TestClassify(TestCase):
    def test_only_text(self):
        content = {"content": "biological psychology",
                   "media": {"image": None, "media": None}}
        act = classify(content)
        self.fail()

    def test_only_image(self):
        content = {"content": "", "media": {
            "image": "attachments/09r2e442o8lppjfeblf7il2rmd.png",
            "media": None}}
        act = classify(content)
        exp = 'ximage_09r2e442o8lppjfeblf7il2rmd_extension_png'
        self.assertEqual(exp, act)

    def test_only_media(self):
        content = {"content": "", "media": {
            "image": None,
            "media": "attachments/3lv2k1fhghfb9ghfb8depnqvdt.mp3"}}
        act = classify(content)
        exp = 'xmedia_3lv2k1fhghfb9ghfb8depnqvdt_extension_mp3'
        self.assertEqual(exp, act)


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