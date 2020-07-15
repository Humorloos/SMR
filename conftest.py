import os

import pytest
from XmindImport.tests.constants import EMPTY_COLLECTION
import smrworld
from XmindImport.tests.constants import SUPPORT_PATH


@pytest.fixture(scope="session")
def empty_anki_collection():
    collection = EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture(scope="session")
def smr_world_for_tests(empty_anki_collection):
    smrworld.FILE_NAME = "smr_world_for_tests.sqlite3"
    smrworld.USER_PATH = SUPPORT_PATH
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()
