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

        self.syncer = XSyncer(col=col, status_file=self.status_file)
        self.syncer.run()
        self.fail()

    def test_col_changes(self):
        # Save original map before synchronization to tempfile
        map_path = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'example map.xmind')
        shutil.copy2(map_path, temp_path)

        col_path = os.path.join(SUPPORT_PATH, 'cols', 'changes',
                                'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)

        # Init test
        self.syncer.run()

        # Restore original version and remove temp file
        shutil.copy(temp_path, map_path)
        os.remove(temp_path)

        self.fail()

    def test_non_leaf_answer_deletion_error(self):
        col_path = os.path.join(
            SUPPORT_PATH, 'cols', 'non_leaf_answer_deletion_error',
            'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)
        with self.assertRaises(ReferenceError):
            self.syncer.run()
