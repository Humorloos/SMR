import pytest
from XmindImport.tests.constants import EMPTY_COLLECTION


@pytest.fixture()
def empty_anki_collection():
    collection = EMPTY_COLLECTION
    yield collection
    collection.close(save=False)
