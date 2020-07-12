import os
import pickle
from unittest import TestCase

import pytest
import xmindimport
from XmindImport.consts import ADDON_PATH
from XmindImport.xmanager import XManager
from XmindImport.xmindimport import XmindImporter
from bs4 import BeautifulSoup

from anki import Collection

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestXmindImporter(TestCase):
    def setUp(self):
        colPath = os.path.join(SUPPORT_PATH, 'empty_smr_col.anki2')
        self.col = Collection(colPath)
        self.map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        self.xmindImporter = XmindImporter(col=self.col, file=self.map)


class TestGetRefManagers(TestXmindImporter):
    def test_example_sheets(self):
        self.xmindImporter.get_ref_managers(self.xmindImporter.x_managers[0])
        self.assertEqual(len(self.xmindImporter.x_managers), 2)


class TestGetValidSheets(TestXmindImporter):
    def test_example_sheets(self):
        act = self.xmindImporter.get_valid_sheets()
        self.assertEqual(act, ['biological psychology', 'clinical psychology'])


class TestImportMap(TestXmindImporter):
    def setUp(self):
        super().setUp()
        importer = self.xmindImporter
        importer.deckId = '1'
        importer.deckName = self.col.decks.get(importer.deckId)['name']
        importer.currentSheetImport = 'biological psychology'
        importer.activeManager = self.xmindImporter.x_managers[0]

    def test_import_biological_psychology(self):
        self.xmindImporter.import_map()
        self.fail()

    def test_whole_example(self):
        importer = self.xmindImporter
        importer.x_managers.append(
            XManager(os.path.join(
                ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
        importer.import_map()
        importer.currentSheetImport = 'clinical psychology'
        importer.import_map()
        importer.activeManager = importer.x_managers[1]
        importer.currentSheetImport = 'general psychology'
        importer.import_map()
        self.assertEqual(1076, len(importer.onto.graph))


class TestGetAnswerDict(TestImportMap):
    def test_dict_for_root(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            root = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xmindImporter.get_answer_dict(root)
        self.fail()

    def test_empty_node(self):
        importer = self.xmindImporter
        xid = '6b0ho6vvcs4pcacchhsgju7513'
        nodeTag = importer.activeManager.getTagById(xid)
        act = self.xmindImporter.get_answer_dict(nodeTag)
        self.fail()

    def test_crosslink_and_text(self):
        importer = self.xmindImporter
        xid = '2koenah8ebavhq2bl2u6u1lh4h'
        nodeTag = importer.activeManager.getTagById(xid)
        act = self.xmindImporter.get_answer_dict(nodeTag)
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
        act = importer.get_questions(parent_answer_dict=answerDict,
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
        ref = 'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: ' \
              'enzymes</li><li>example: MAO</li><li>splits up'
        act = self.xmindImporter.get_questions(parent_answer_dict=answerDict,
                                               sort_id='|{|{{{|',
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
        act = importer.find_answer_dicts(parents=parents, question=question,
                                         sort_id='{', ref=ref, content=content)
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
        act = importer.find_answer_dicts(parents=parents, question=question,
                                         sort_id='{', ref=ref, content=content)
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
        act = importer.find_answer_dicts(parents=parents, question=question,
                                         sort_id='{', ref=ref, content=content)
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
        act = importer.find_answer_dicts(parents=parents, question=question,
                                         sort_id='{', ref=ref, content=content)
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
        ref = 'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: ' \
              'enzymes</li><li>example: MAO</li><li>splits up</li>'
        content = {'content': 'are', 'media': {'image': None, 'media': None}}
        act = importer.find_answer_dicts(
            parents=parents, question=question, sort_id='{', ref=ref,
            content=content)
        self.assertEqual(4, len(act[0]['concepts'][0].Parent))

    def test_bridge_question(self):
        importer = self.xmindImporter
        xid = '49a1au2r1i2mvpkufnrs18lb2h'
        question = importer.activeManager.getTagById(xid)
        parent = importer.onto.Concept('MAO')
        ref = 'biological psychology<li>investigates: information transfer and processing</li><li>modulated by: ' \
              'enzymes</li><li>example: MAO</li>'
        parent.Image = None
        parent.Media = None
        parent.Xid = '7blr5ubl6uf6c9beflm85jte19'
        parents = [parent]
        content = {'content': 'difference to MAO', 'media': {'image': None,
                                                             'media': None}}
        sortId = '|{|{{{}'
        act = importer.find_answer_dicts(
            parents=parents, question=question, sort_id=sortId, ref=ref,
            content=content)
        self.assertIsNone(act)
        self.assertEqual(
            'MAO is not a neurotransmitter', importer.onto.search(
                iri='*#MAO')[0].difference_to_MAO[0].name)


class TestImportOntology(TestImportMap):
    def setUp(self):
        super().setUp()
        importer = self.xmindImporter
        importer.x_managers.append(
            XManager(os.path.join(
                ADDON_PATH, 'resources', 'example_general_psychology.xmind')))
        importer.import_map()
        importer.currentSheetImport = 'clinical psychology'
        importer.import_map()
        importer.activeManager = importer.x_managers[1]
        importer.currentSheetImport = 'general psychology'
        importer.import_map()

    def test_example(self):
        importer = self.xmindImporter
        importer.import_ontology()
        self.fail()


# TODO: doesn't work, questionList has wrong ids, fix
class TestNoteFromQuestionList(TestImportOntology):
    def test_multiple_answers(self):
        importer = self.xmindImporter
        questionList = [(315, 317, 318), (315, 317, 319)]
        act = importer.note_from_question_list(questionList)
        self.fail()

    def test_bridge_parent(self):
        importer = self.xmindImporter
        questionList = [(328, 346, 325)]
        act = importer.note_from_question_list(questionList)
        self.fail()


class TestGetXMindMeta(TestImportOntology):
    def test_multiple_answers(self):
        importer = self.xmindImporter
        noteData = pickle.load(
            open(os.path.join(SUPPORT_PATH, 'xmindImporter', 'noteData.p'),
                 'rb'))
        act = importer.get_xmind_meta(noteData)
        self.fail()


class TestUpdateStatus(TestImportOntology):
    def setUp(self):
        super().setUp()
        self.xmindImporter.import_ontology()

    def test_update_status(self):
        importer = self.xmindImporter
        importer.update_status()
        os.remove(importer.statusManager.status_file)
        self.fail()


@pytest.fixture
def xmind_importer():
    collection_path = os.path.join(SUPPORT_PATH, 'empty_smr_col.anki2')
    collection = Collection(collection_path)
    test_map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    yield xmindimport.XmindImporter(col=collection, file=test_map)


def test_run(mocker, xmind_importer):
    """
    Test for general functionality
    """
    # given
    cut = xmind_importer
    mocker.patch("xmindimport.DeckSelectionDialog")
    mocker.patch.object(cut, "mw")
    mocker.patch.object(cut, "init_import")

    # when
    cut.run()

    # then
    assert cut.mw.progress.finish.call_count == 1
    assert cut.init_import.call_count == 1


def test_run_aborts_when_canceling_import(mocker, xmind_importer):
    """
    Test that run is aborted when user clicks cancel in deck selection dialog
    """
    # given
    cut = xmind_importer
    mocker.patch("xmindimport.DeckSelectionDialog")
    xmindimport.DeckSelectionDialog.return_value = xmindimport.DeckSelectionDialog
    xmindimport.DeckSelectionDialog.exec.return_value = None
    xmindimport.DeckSelectionDialog.get_inputs.return_value = {'running': False}
    mocker.patch.object(cut, "mw")
    mocker.patch.object(cut, "init_import")

    # when
    cut.run()

    # then
    assert cut.log == [xmindimport.IMPORT_CANCELED_MESSAGE]
    assert cut.mw.progress.finish.call_count == 1
    assert not cut.init_import.called
