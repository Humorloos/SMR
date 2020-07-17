import os

import bs4
import pytest
import smrworld
import xmanager
import XmindImport.tests.constants as cts


@pytest.fixture(scope="session")
def empty_anki_collection():
    collection = cts.EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture
def empty_smr_world():
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    test_world = "testworld.sqlite3"
    standard_world = smrworld.FILE_NAME
    smrworld.FILE_NAME = test_world
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smrworld.FILE_NAME = standard_world
    smr_world.close()
    os.unlink(os.path.join(smrworld.USER_PATH, test_world))


@pytest.fixture(scope="session")
def _smr_world_for_tests_session(empty_anki_collection):
    smrworld.FILE_NAME = "smr_world_for_tests.sqlite3"
    smrworld.USER_PATH = cts.SUPPORT_PATH
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()


@pytest.fixture()
def smr_world_for_tests(_smr_world_for_tests_session):
    smr_world = _smr_world_for_tests_session
    yield smr_world
    smr_world.graph.db.rollback()


@pytest.fixture
def x_manager():
    yield xmanager.XManager(cts.EXAMPLE_MAP_PATH)


@pytest.fixture
def tag_for_tests():
    with open(os.path.join(cts.SUPPORT_PATH, 'xmindImporter', 'content.xml'), 'r') as file:
        tag = bs4.BeautifulSoup(file.read(), features='html.parser').topic
        file.close()
    yield tag
