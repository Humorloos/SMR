import os
from unittest import TestCase

from consts import ADDON_PATH
from smr import CGraph

from anki import Collection
from anki.collection import _Collection

class TestCGraph(TestCase):
    def setUp(self):
        colPath = os.path.join(ADDON_PATH, 'tests', 'support',
                               'collection.anki2')
        _Collection.defaultSchedulerVersion = 1
        self.col = Collection(colPath)
        self.col.conf['activeDecks'] = [1]
        self.cgraph = CGraph(self.col)

class TestInit(TestCGraph):
    def test_col(self):
        self.assertEqual(self.cgraph.col, self.col)