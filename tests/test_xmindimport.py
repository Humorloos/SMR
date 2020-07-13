import os

import pytest
import xmindimport
from consts import ADDON_PATH


@pytest.fixture
def xmind_importer(empty_anki_collection):
    test_map = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
    yield xmindimport.XmindImporter(col=empty_anki_collection, file=test_map)


def test_run(mocker, xmind_importer):
    """
    Test for general functionality
    """
    # given
    cut = xmind_importer
    mocker.patch("xmindimport.DeckSelectionDialog")
    mocker.patch.object(cut, "mw")
    mocker.patch.object(cut, "initialize_import")

    # when
    cut.run()

    # then
    assert cut.mw.progress.finish.call_count == 1
    assert cut.initialize_import.call_count == 1


def test_run_aborts_when_canceling_import(mocker, xmind_importer):
    """
    Test that run is aborted when user clicks cancel in deck selection dialog
    """
    # given
    cut = xmind_importer
    mocker.patch("xmindimport.DeckSelectionDialog")
    xmindimport.DeckSelectionDialog.return_value = xmindimport.DeckSelectionDialog
    xmindimport.DeckSelectionDialog.exec.return_value = None
    xmindimport.DeckSelectionDialog.get_inputs.return_value = {'running': False}
    mocker.patch.object(cut, "mw")
    mocker.patch.object(cut, "initialize_import")

    # when
    cut.run()

    # then
    assert cut.log == [xmindimport.IMPORT_CANCELED_MESSAGE]
    assert cut.mw.progress.finish.call_count == 1
    assert not cut.initialize_import.called


def test_initialize_import(mocker, xmind_importer):
    # given
    cut = xmind_importer
    deck_name = 'my deck'
    deck_id = 'my deck_id'
    valid_sheet = 'valid sheet'
    mocker.patch.object(cut, 'acquire_sheets_containing_concept_maps', return_value=valid_sheet)
    mocker.patch.object(cut.col.decks, 'get', return_value={'name': deck_name})
    mocker.patch.object(cut, 'mw')
    mocker.patch('xmindimport.XOntology')
    mocker.patch.object(cut, 'import_sheets')
    # when
    xmind_importer.initialize_import(deck_id=deck_id, repair=False)
    # then
    cut.acquire_sheets_containing_concept_maps.assert_called_once()
    cut.mw.progress.start.assert_called_once()
    cut.import_sheets.assert_called_with(valid_sheet)


def test_acquire_sheets_containing_concept_maps(xmind_importer):
    # given
    cut = xmind_importer
    # when
    act = cut.acquire_sheets_containing_concept_maps()
    # then
    assert act == ['biological psychology', 'clinical psychology']
