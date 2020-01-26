import os

from unittest import TestCase

from anki import Collection

from XmindImport.consts import ADDON_PATH
from XmindImport.xnotemanager import XNoteManager, FieldTranslator

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


class TestFieldTranslator(TestCase):
    def setUp(self):
        self.field_translator = FieldTranslator()


class FieldFromClass(TestFieldTranslator):
    def test_only_text(self):
        translator = self.field_translator
        content = 'MAO_is_not_a_neurotransmitter'
        act = translator.field_from_class(content)
        exp = 'MAO is not a neurotransmitter'
        self.assertEqual(exp, act)

    def test_only_image(self):
        translator = self.field_translator
        content = '<img:09r2e442o8lppjfeblf7il2rmd.png>'
        act = translator.field_from_class(content)
        exp = '<img src="09r2e442o8lppjfeblf7il2rmd.png">'
        self.assertEqual(exp, act)

    def test_only_media(self):
        translator = self.field_translator
        content = '<media:3lv2k1fhghfb9ghfb8depnqvdt.mp3>'
        act = translator.field_from_class(content)
        exp = '[sound:3lv2k1fhghfb9ghfb8depnqvdt.mp3]'
        self.assertEqual(exp, act)
