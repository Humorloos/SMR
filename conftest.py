import os
from imp import reload

import bs4
import pytest
import smrworld
import xmanager
import XmindImport.tests.constants as cts
import xontology
from config import get_or_create_smr_world

from anki import Collection


TEST_WORLD_NAME = "testworld.sqlite3"


@pytest.fixture(scope="session")
def empty_anki_collection() -> Collection:
    collection = cts.EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture()
def patch_smr_world() -> None:
    standard_world = smrworld.FILE_NAME
    smrworld.FILE_NAME = TEST_WORLD_NAME
    yield
    smrworld.FILE_NAME = standard_world
    os.unlink(os.path.join(smrworld.USER_PATH, TEST_WORLD_NAME))


@pytest.fixture
def empty_smr_world(patch_smr_world) -> smrworld.SmrWorld:
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()


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


@pytest.fixture()
def x_ontology(mocker, patch_smr_world) -> xontology.XOntology:
    mocker.patch('xontology.mw')
    xontology.mw.smr_world = get_or_create_smr_world()
    mocker.spy(xontology.XOntology, "_set_up_classes")
    x_ontology = xontology.XOntology("99999")
    yield x_ontology
    xontology.mw.smr_world.close()
