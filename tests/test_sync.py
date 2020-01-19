import os

from unittest import TestCase

from anki import Collection

from XmindImport.sync import XSyncer
from XmindImport.consts import ADDON_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'syncer')

class TestXSyncer(TestCase):
    def setUp(self):
        colPath = os.path.join(SUPPORT_PATH, 'cols', 'no_changes',
                               'collection.anki2')
        col = Collection(colPath)
        self.syncer = XSyncer(col=col)

    def test_run(self):
        self.fail()
