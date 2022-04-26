import os

import pytest
from anki.collection import Collection

from smr.tests.constants import TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH, PATH_EXAMPLE_MAP_DEFAULT, TEST_DECK_NAME
from smr.xminder import XmindImporter
from smr.template import add_x_model


@pytest.fixture(scope="function")
def empty_anki_collection_function() -> Collection:
    try:
        os.unlink(TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH)
    except FileNotFoundError:
        pass
    collection = Collection(TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH)
    add_x_model(collection)
    yield collection
    collection.close()


def test_import_example_map(empty_anki_collection_function):
    # Given
    N_CARDS_EXAMPLE_MAP = 28
    importer = XmindImporter(col=empty_anki_collection_function, file=PATH_EXAMPLE_MAP_DEFAULT)
    test_deck_id = empty_anki_collection_function.decks.id(name=TEST_DECK_NAME)
    importer.deckId = test_deck_id
    import_data = {
        'sheet': importer.soup('sheet')[0],
        'tag': "hi",
        'deckId': test_deck_id,
    }
    importer.currentSheetImport = import_data
    importer.currentSheetImport['ID'] = importer.currentSheetImport['sheet']['id']
    importer.notesToAdd[importer.currentSheetImport['ID']] = []
    importer.log = [['Added', 0, 'notes'], ['updated', 0, 'notes'], ['removed', 0, 'notes']]

    # When
    importer.importMap(sheetImport=import_data)
    for sheetId, noteList in importer.notesToAdd.items():
        importer.maybeSync(sheetId=sheetId, noteList=noteList)

    # Then
    n_cards_imported = len(empty_anki_collection_function.db.execute("select * from cards where did = ?", test_deck_id))
    assert n_cards_imported == N_CARDS_EXAMPLE_MAP
