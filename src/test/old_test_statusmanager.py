from unittest import TestCase

from main.statusmanager import StatusManager


class TestStatusManager(TestCase):
    def setUp(self):
        self.statusmanager = StatusManager()


class TestAddNew(TestStatusManager):
    def test_add_new(self):
        manager = self.statusmanager
