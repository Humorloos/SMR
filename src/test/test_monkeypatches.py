import pickle
from unittest.mock import MagicMock

from pytest import fail

import aqt.importing
import main.monkeypatches
import test.constants as cts
from main.consts import X_MODEL_NAME
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO
from main.template import add_x_model


def test_patch_import_diaglog(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(aqt.importing.ImportDialog, 'exec_')
    mocker.patch('main.monkeypatches.DeckSelectionDialog')
    mocker.patch('main.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    # when
    aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # then
    assert aqt.importing.ImportDialog.exec_.call_count == 0
    assert main.monkeypatches.tooltip.call_count == 1
    assert importer.initialize_import.call_count == 1


def test_patch_import_diaglog_interrupts_if_deck_selection_dialog_not_running(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(aqt.importing.ImportDialog, 'exec_')
    mocker.patch('main.monkeypatches.DeckSelectionDialog')
    mocker.patch('main.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    main.monkeypatches.DeckSelectionDialog.return_value = main.monkeypatches.DeckSelectionDialog
    main.monkeypatches.DeckSelectionDialog.get_inputs.return_value = DeckSelectionDialogUserInputsDTO(running=False)
    # when
    aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # assert
    assert aqt.importing.ImportDialog.exec_.call_count == 0
    main.monkeypatches.tooltip.assert_called_once_with(main.monkeypatches.IMPORT_CANCELED_MESSAGE)
    assert importer.initialize_import.call_count == 0


def test_patch_new_data(xmind_importer, smr_world_for_tests):
    # given
    next_note_id = 1
    foreign_note = pickle.loads(cts.EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE)
    importer = xmind_importer
    add_x_model(importer.col)
    importer.model = importer.col.models.byName(X_MODEL_NAME)
    importer._fmap = importer.col.models.fieldMap(importer.model)
    importer._nextID = next_note_id
    importer._ids = []
    importer._cards = []
    importer.smr_world = smr_world_for_tests
    # when
    importer.newData(foreign_note)
    # then
    assert importer.smr_world.graph.execute("SELECT * FROM smr_notes").fetchone()[:2] == (
        next_note_id, cts.EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID)


def test_patch_update_cards(xmind_importer):
    # when
    try:
        xmind_importer.updateCards()
    # then
    except AttributeError:
        fail("Unexpected AttributeError, updateCards() was probably called.")
