import os, tempfile, shutil

from unittest import TestCase

from anki import Collection

from XmindImport.sync import XSyncer
from XmindImport.consts import ADDON_PATH, USER_PATH

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support', 'syncer')


class TestRun(TestCase):
    def setUp(self):
        self.status_file = os.path.join(USER_PATH, 'status.json')

    def test_no_changes(self):
        colPath = os.path.join(SUPPORT_PATH, 'cols', 'no_changes',
                               'collection.anki2')
        col = Collection(colPath)

        self.syncer = XSyncer(col=col, status_file=self.status_file)
        self.syncer.run()
        self.fail()

    def test_col_changes(self):
        # Save original map before synchronization to tempfile
        files_2_conserve = ['example map.xmind',
                            'example_general_psychology.xmind']
        temp_dir = tempfile.gettempdir()
        paths = [{'map': os.path.join(ADDON_PATH, 'resources', f),
                  'temp': os.path.join(temp_dir, f)} for f in files_2_conserve]
        for path in paths:
            shutil.copy2(path['map'], path['temp'])

        col_path = os.path.join(SUPPORT_PATH, 'cols', 'changes',
                                'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)

        # Init test
        self.syncer.run()

        # Restore original version and remove temp file
        for path in paths:
            shutil.copy(path['temp'], path['map'])
            os.remove(path['temp'])

        self.fail()

    def test_map_changes(self):
        # Save original map before synchronization to tempfile and change it
        # to map with changes
        files_2_conserve = ['example map.xmind',
                            'example_general_psychology.xmind']
        temp_dir = tempfile.gettempdir()
        paths = [{
            'change': os.path.join(SUPPORT_PATH, 'maps', 'changes', f),
            'resource': os.path.join(ADDON_PATH, 'resources', f),
            'temp': os.path.join(temp_dir, f)} for f in files_2_conserve]
        paths.append({'resource': os.path.join(
            SUPPORT_PATH, 'cols', 'no_changes', 'collection.anki2'),
                      'temp': os.path.join(temp_dir, 'collection.anki2'),
                      'change': None})
        paths.append({'resource': os.path.join(USER_PATH, 'status.json'),
                      'temp': os.path.join(temp_dir, 'status.json'),
                      'change': None})
        paths.append({'resource': os.path.join(USER_PATH, '1579442668731.rdf'),
                      'temp': os.path.join(temp_dir, '1579442668731.rdf'),
                      'change': None})
        for path in paths:
            shutil.copy2(path['resource'], path['temp'])
            if path['change']:
                shutil.copy2(path['change'], path['resource'])

        col_path = os.path.join(SUPPORT_PATH, 'cols', 'no_changes',
                                'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)

        # Init test
        self.syncer.run()

        # Restore original version and remove temp file
        for path in paths:
            shutil.copy(path['temp'], path['resource'])
            os.remove(path['temp'])

    def test_non_leaf_answer_deletion_error(self):
        col_path = os.path.join(
            SUPPORT_PATH, 'cols', 'non_leaf_answer_deletion_error',
            'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)
        with self.assertRaises(ReferenceError):
            self.syncer.run()

    def test_answer_added_error(self):
        col_path = os.path.join(
            SUPPORT_PATH, 'cols', 'answer_added_error',
            'collection.anki2')
        col = Collection(col_path)
        self.syncer = XSyncer(col=col, status_file=self.status_file)
        with self.assertRaises(ReferenceError):
            self.syncer.run()