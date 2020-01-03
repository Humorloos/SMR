import os
import zipfile

from unittest import TestCase

from bs4 import BeautifulSoup

from XmindImport.consts import ADDON_PATH
from XmindImport.utils import getNodeContent, getNodeTitle, getNodeImg

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestGetNodeContent(TestCase):
    def test_getNodeContent(self):
        zipFile = zipfile.ZipFile(
            os.path.join(ADDON_PATH, 'resources', 'example map.xmind'),
            'r').read('content.xml')
        tagList = BeautifulSoup(zipFile, features='html.parser')('topic')
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = getNodeContent(tagList=tagList, tag=tag)
        self.assertEqual(act[0], 'biological psychology')
        self.assertEqual(act[1]['image'], None)
        self.assertEqual(act[1]['media'], None)


class TestGetNodeTitle(TestCase):
    def test_getNodeTitle(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = getNodeTitle(tag)
        self.assertEqual(act, 'biological psychology')


class TestGetNodeImg(TestCase):
    def test_getNodeImage(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = getNodeImg(tag)
        self.assertEqual(act, None)
