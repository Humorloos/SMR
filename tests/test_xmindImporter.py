import os

from unittest import TestCase

from tests.shared import getEmptyCol

from XmindImport.consts import ADDON_PATH
from XmindImport.xminder import XmindImporter

class TestXmindImporter(TestCase):
    def setUp(self):
        self.col = getEmptyCol()
        self.map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        self.xmindImporter = XmindImporter(col=self.col, file=self.map)

class TestInit(TestXmindImporter):
    def test_model(self):
        print('hi')
