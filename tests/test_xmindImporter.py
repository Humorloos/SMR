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
        # self.assertEqual()
        print('hi')


class TestGetXSheets(TestXmindImporter):
    def test_example_sheets(self):
        act = self.xmindImporter.get_x_sheets(self.xmindImporter.soup,
                                              self.xmindImporter.file)
        self.assertEqual(len(act[0]), 3)
        self.assertEqual(act[1], 'example map')


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
