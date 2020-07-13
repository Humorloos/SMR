import pytest
from XmindImport.tests.constants import EMPTY_COLLECTION
from smrworld import SmrWorld


@pytest.fixture(scope="session")
def empty_anki_collection():
    collection = EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture(scope="session")
def empty_smr_world(empty_anki_collection):
    smr_world = SmrWorld(anki_collection=empty_anki_collection)
    yield smr_world
    smr_world.close()
