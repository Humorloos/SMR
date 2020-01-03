import os
import zipfile

from unittest import TestCase

from bs4 import BeautifulSoup

from XmindImport.consts import ADDON_PATH
from XmindImport.utils import getNodeContent, getNodeTitle

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestGetNodeTitle(TestCase):
    def test_getNodeTitle(self):
        with open(os.path.join(SUPPORT_PATH, 'xmindImporter',
                               'sheet_biological_psychology.xml'), 'r') as file:
            tag = BeautifulSoup(file.read(), features='html.parser').topic
        act = getNodeTitle(tag)
        self.assertEqual(act, 'biological psychology')
