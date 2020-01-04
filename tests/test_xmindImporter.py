import os
import pickle

from unittest import TestCase

from bs4 import BeautifulSoup

from anki import Collection

from XmindImport.consts import ADDON_PATH
from XmindImport.xmindimport import XmindImporter

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestXmindImporter(TestCase):
    def setUp(self):
        colPath = os.path.join(SUPPORT_PATH, 'collection.anki2')
        self.col = Collection(colPath)
        self.map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        self.xmindImporter = XmindImporter(col=self.col, file=self.map)


class TestGetXSheets(TestXmindImporter):
    def test_example_sheets(self):
        act = self.xmindImporter.get_x_sheets(
            self.xmindImporter.xManagers['root'])
        self.assertEqual(len(act[0]), 3)


class TestImportSheets(TestXmindImporter):
    def test_import_example(self):
        selectedSheets = list()
        sheet_tags = self.xmindImporter.soup('sheet')
        for sheet_tag in sheet_tags:
            sheet_dict = dict(sheet=sheet_tag, tag="test", deckId="1",
                              repair=False)
            selectedSheets.append(sheet_dict)
        self.xmindImporter.importSheets(selectedSheets)
        print('hi')
