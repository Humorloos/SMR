import os
import zipfile

from unittest import TestCase

from bs4 import BeautifulSoup

from XmindImport.consts import ADDON_PATH
from XmindImport.xmanager import XManager

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestXManager(TestCase):
    def setUp(self):
        self.file = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        self.xManager = XManager(self.file)


class TestGetNodeContent(TestXManager):
    def test_getNodeContent(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xManager.getNodeContent(tag=tag)
        self.assertEqual(act['content'], 'biological psychology')
        self.assertEqual(act['media']['image'], None)
        self.assertEqual(act['media']['media'], None)


class TestGetNodeTitle(TestXManager):
    def test_getNodeTitle(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xManager.getNodeTitle(tag)
        self.assertEqual(act, 'biological psychology')


class TestGetNodeImg(TestXManager):
    def test_no_image(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xManager.getNodeImg(tag)
        self.assertEqual(act, None)


class TestGetNodeHyperlink(TestXManager):
    def test_no_hyperlink(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xManager.getNodeHyperlink(tag)
        self.assertEqual(act, None)


class TestIsEmptyNode(TestXManager):
    def test_not_empty(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = self.xManager.isEmptyNode(tag)
        self.assertEqual(act, False)
