import pytest
import smrworld
import xmanager
from XmindImport.tests.constants import EMPTY_COLLECTION, EXAMPLE_MAP_PATH, SUPPORT_PATH


@pytest.fixture(scope="session")
def empty_anki_collection():
    collection = EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture(scope="session")
def smr_world_for_tests_session(empty_anki_collection):
    smrworld.FILE_NAME = "smr_world_for_tests.sqlite3"
    smrworld.USER_PATH = SUPPORT_PATH
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()


@pytest.fixture()
def smr_world_for_tests(smr_world_for_tests_session):
    smr_world = smr_world_for_tests_session
    yield smr_world
    smr_world.graph.db.rollback()


@pytest.fixture
def x_manager():
    yield xmanager.XManager(EXAMPLE_MAP_PATH)