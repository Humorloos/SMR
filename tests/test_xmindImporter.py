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

    def test_empty_node(self):
        importer = self.xmindImporter
        xid = '6b0ho6vvcs4pcacchhsgju7513'
        nodeTag = importer.activeManager.getTagById(xid)
        act = self.xmindImporter.getAnswerDict(nodeTag)
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
        concept = [concept]
        answerDict = {'nodeTag': nodeTag, 'isAnswer': True, 'aId': str(0),
                      'crosslink': None, 'concepts': concept}
        act = self.xmindImporter.getQuestions(parentAnswerDict=answerDict,
                                              ref='biological psychology')
        self.fail()

    def test_questions_following_multiple_answers(self):
        importer = self.xmindImporter
        xid = '6b0ho6vvcs4pcacchhsgju7513'
        nodeTag = importer.activeManager.getTagById(xid)
        concepts = list()
        concepts.append(importer.onto.Concept('Serotonin'))
        concepts.append(importer.onto.Concept('dopamine'))
        concepts.append(importer.onto.Concept('adrenaline'))
        concepts.append(importer.onto.Concept('noradrenaline'))
        for parent in concepts:
            parent.Image = None
            parent.Media = None
        concepts[0].Xid = '56ru8hj8k8361ppfrftrbahgvv'
        concepts[1].Xid = '03eokjlomuockpeaqn2923nvvp'
        concepts[2].Xid = '3f5lmmd8mjhe3gkbnaih1m9q8j'
        concepts[3].Xid = '73mo29opsuegqobtttlt2vbaqj'
        answerDict = {'nodeTag': nodeTag, 'isAnswer': False, 'aId': str(0),
                      'crosslink': None, 'concepts': concepts}
        ref = 'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up'
        act = self.xmindImporter.getQuestions(parentAnswerDict=answerDict, sortId='|{|{{{|',
                                              ref=ref)
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
        parents = [parent]
        content = {'content': '', 'media': {'image': None, 'media': None}}
        act = importer.findAnswerDicts(parents=parents, question=question,
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
        parents = [parent]
        content = {'content': 'investigates', 'media': {'image': None,
                                                        'media': None}}
        act = importer.findAnswerDicts(parents=parents, question=question,
                                       sortId='{', ref=ref, content=content)
        self.fail()

    def test_question_with_spaces(self):
        importer = self.xmindImporter
        xid = '077tf3ovn4gc1j1dqte7or33fl'
        question = importer.activeManager.getTagById(xid)
        parent = importer.onto.Root('biological psychology')
        ref = 'biological psychology'
        parent.Image = None
        parent.Media = None
        parent.Xid = xid
        parents = [parent]
        content = {'content': 'difference to MAO', 'media': {'image': None,
                                                             'media': None}}
        act = importer.findAnswerDicts(parents=parents, question=question,
                                       sortId='{', ref=ref, content=content)
        self.assertIn('difference_to_MAO', map(lambda p: p.name,
                                               act[0]['concept'].Parent[
                                                   0].get_properties()))

    def test_containing_bridge_answer(self):
        importer = self.xmindImporter
        xid = '61irckf1nloq42brfmbu0ke92v'
        question = importer.activeManager.getTagById(xid)
        parent = importer.onto.Root('biological psychology')
        ref = 'biological psychology'
        parent.Image = None
        parent.Media = None
        parent.Xid = xid
        parents = [parent]
        content = {'content': 'splits up', 'media': {'image': None,
                                                             'media': None}}
        act = importer.findAnswerDicts(parents=parents, question=question,
                                       sortId='{', ref=ref, content=content)
        self.assertIn('difference_to_MAO', map(lambda p: p.name,
                                               act[0]['concept'].Parent[
                                                   0].get_properties()))

    def test_following_multiple_answers(self):
        importer = self.xmindImporter
        xid = '6iivm8tpoqj2c0euaabtput14l'
        question = importer.activeManager.getTagById(xid)
        parents = list()
        parents.append(importer.onto.Concept('Serotonin'))
        parents.append(importer.onto.Concept('dopamine'))
        parents.append(importer.onto.Concept('adrenaline'))
        parents.append(importer.onto.Concept('noradrenaline'))
        for parent in parents:
            parent.Image = None
            parent.Media = None
        parents[0].Xid = '56ru8hj8k8361ppfrftrbahgvv'
        parents[1].Xid = '03eokjlomuockpeaqn2923nvvp'
        parents[2].Xid = '3f5lmmd8mjhe3gkbnaih1m9q8j'
        parents[3].Xid = '73mo29opsuegqobtttlt2vbaqj'
        ref = 'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up</li>'
        content = {'content': 'are', 'media': {'image': None, 'media': None}}
        act = importer.findAnswerDicts(parents=parents, question=question,
                                       sortId='{', ref=ref, content=content)
        self.assertEqual(4, len(act[0]['concepts'][0].Parent))