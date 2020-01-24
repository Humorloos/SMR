import os, tempfile, shutil

from unittest import TestCase

from anki import Collection

from XmindImport.sync import XSyncer
from XmindImport.consts import ADDON_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'syncer')


class TestRun(TestCase):
    def setUp(self):
        self.status_file = os.path.join(SUPPORT_PATH, 'status.json')

    def test_no_changes(self):
        colPath = os.path.join(SUPPORT_PATH, 'cols', 'no_changes',
                               'collection.anki2')
        col = Collection(colPath)

        # status_file = None
        self.syncer = XSyncer(col=col, status_file=self.status_file)
        self.syncer.run()
        self.fail()
