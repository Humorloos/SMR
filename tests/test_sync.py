import os

from unittest import TestCase

from anki import Collection

from XmindImport.sync import XSyncer
from XmindImport.consts import ADDON_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')

class TestXSyncer(TestCase):
    def setUp(self):
        colPath = os.path.join(SUPPORT_PATH, 'syncer',
                               'collection.anki2')
        col = Collection(colPath)
        self.syncer = XSyncer(col=col)

    def test_run(self):
        self.fail()
