from unittest.mock import MagicMock

import qt.aqt.importing
import smr.monkeypatches as monkeypatches
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO


def test_patch_import_diaglog(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(qt.aqt.importing.ImportDialog, 'exec_')
    mocker.patch('smr.monkeypatches.DeckSelectionDialog')
    mocker.patch('smr.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    mocker.patch.object(importer, "finish_import")
    # when
    qt.aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # then
    assert qt.aqt.importing.ImportDialog.exec_.call_count == 0
    assert monkeypatches.tooltip.call_count == 1
    assert importer.initialize_import.call_count == 1
    assert importer.finish_import.call_count == 1


def test_patch_import_diaglog_interrupts_if_deck_selection_dialog_not_running(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(qt.aqt.importing.ImportDialog, 'exec_')
    mocker.patch('smr.monkeypatches.DeckSelectionDialog')
    mocker.patch('smr.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    monkeypatches.DeckSelectionDialog.return_value = monkeypatches.DeckSelectionDialog
    monkeypatches.DeckSelectionDialog.get_inputs.return_value = DeckSelectionDialogUserInputsDTO(running=False)
    # when
    qt.aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # assert
    assert qt.aqt.importing.ImportDialog.exec_.call_count == 0
    monkeypatches.tooltip.assert_called_once_with(monkeypatches.IMPORT_CANCELED_MESSAGE)
    assert importer.initialize_import.call_count == 0