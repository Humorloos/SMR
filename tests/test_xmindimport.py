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
