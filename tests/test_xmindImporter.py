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


class TestGetRefManagers(TestXmindImporter):
    def test_example_sheets(self):
        self.xmindImporter.getRefManagers(self.xmindImporter.xManagers[0])
        self.assertEqual(len(self.xmindImporter.xManagers), 2)


class TestGetValidSheets(TestXmindImporter):
    def test_example_sheets(self):
        act = self.xmindImporter.getValidSheets()
        self.assertEqual(act, ['biological psychology', 'clinical psychology'])

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
