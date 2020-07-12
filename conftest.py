import pytest
from XmindImport.tests.constants import EMPTY_COLLECTION_PATH

from anki import Collection


@pytest.fixture()
def empty_anki_collection():
    yield Collection(EMPTY_COLLECTION_PATH)