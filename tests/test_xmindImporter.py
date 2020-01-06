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


class TestImportMap(TestXmindImporter):
    def setUp(self):
        super().setUp()
        self.xmindImporter.deckId = '1'
        self.xmindImporter.currentSheetImport = 'biological psychology'
        self.xmindImporter.activeManager = self.xmindImporter.xManagers[0]

    def test_import_example(self):
        self.xmindImporter.importMap()
        print('hi')


class TestGetAnswerDict(TestImportMap):
    def test_dict_for_root(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            root = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xmindImporter.getAnswerDict(root)
        self.fail()


class TestGetQuestions(TestImportMap):
    def test_questions_for_root(self):
        importer = self.xmindImporter
        xid = '0pbme7b9sg9en8qqmmn9jj06od'
        nodeTag = importer.activeManager.getTagById(xid)
        concept = importer.onto.Root('biological psychology')
        concept.Image = None
        concept.Media = None
        concept.Xid = xid
        answerDict = {'nodeTag': nodeTag, 'isAnswer': True, 'aId': str(0),
                      'crosslink': None, 'concept': concept}
        act = self.xmindImporter.getQuestions(answerDict=answerDict,
                                              ref='biological psychology')
        self.fail()


class TestFindAnswerDicts(TestImportMap):
    def test_crosslink(self):
        importer = self.xmindImporter
        xid = '32dt8d2dflh4lr5oqc2oqqad28'
        question = importer.activeManager.getTagById(xid)
        parent = importer.onto.Root('biological psychology')
        ref = 'biological psychology'
        parent.Image = None
        parent.Media = None
        parent.Xid = xid
        content = {'content': '', 'media': {'image': None, 'media': None}}
        act = importer.findAnswerDicts(parent=parent, question=question,
                                       sortId='{', ref=ref, content=content)
        self.fail()

    def test_two_answers_no_media(self):
        importer = self.xmindImporter
        xid = '4kdqkutdha46uns1j8jndi43ht'
        question = importer.activeManager.getTagById(xid)
        parent = importer.onto.Root('biological psychology')
        ref = 'biological psychology'
        parent.Image = None
        parent.Media = None
        parent.Xid = xid
        content = {'content': 'investigates', 'media': {'image': None,
                                                        'media': None}}
        act = importer.findAnswerDicts(parent=parent, question=question,
                                       sortId='{', ref=ref, content=content)
        self.fail()
