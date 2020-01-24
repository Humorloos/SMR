import os

from unittest import TestCase

from anki import Collection

from XmindImport.consts import ADDON_PATH
from XmindImport.xnotemanager import XNoteManager

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')


class TestXNoteManager(TestCase):
    def setUp(self):
        col = Collection(os.path.join(SUPPORT_PATH, 'syncer',
                                      'cols', 'no_changes', 'collection.anki2'))
        self.note_manager = XNoteManager(col)


class TestGetXmindFiles(TestXNoteManager):
    def test_get_xmind_files(self):
        act = self.note_manager.get_xmind_files()
        self.fail()


class TestGetLocal(TestXNoteManager):
    def test_get_local(self):
        manager = self.note_manager
        file = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        act = manager.get_local(file=file)
        self.fail()

    def test_changes_general_psycholog(self):
        col = Collection(os.path.join(SUPPORT_PATH, 'syncer',
                                      'cols', 'changes', 'collection.anki2'))
        manager = XNoteManager(col)
        file = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
        act = manager.get_local(file=file)
        self.fail()
