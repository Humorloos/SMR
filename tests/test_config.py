from unittest import TestCase
from XmindImport.config import set_up_ontology


class Test(TestCase):
    def test_set_up_ontology(self):
        set_up_ontology()
        self.fail()
