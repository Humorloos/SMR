from unittest.mock import MagicMock

import aqt.importing
import smr.monkeypatches as monkeypatches
from smr.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO


def test_patch_import_diaglog(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(aqt.importing.ImportDialog, 'exec_')
    mocker.patch('smr.monkeypatches.DeckSelectionDialog')
    mocker.patch('smr.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    mocker.patch.object(importer, "finish_import")
    # when
    aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # then
    assert aqt.importing.ImportDialog.exec_.call_count == 0
    assert monkeypatches.tooltip.call_count == 1
    assert importer.initialize_import.call_count == 1
    assert importer.finish_import.call_count == 1


def test_patch_import_diaglog_interrupts_if_deck_selection_dialog_not_running(xmind_importer, mocker):
    # given
    importer = xmind_importer
    mocker.spy(aqt.importing.ImportDialog, 'exec_')
    mocker.patch('smr.monkeypatches.DeckSelectionDialog')
    mocker.patch('smr.monkeypatches.tooltip')
    mocker.patch.object(importer, 'initialize_import')
    monkeypatches.DeckSelectionDialog.return_value = monkeypatches.DeckSelectionDialog
    monkeypatches.DeckSelectionDialog.get_inputs.return_value = DeckSelectionDialogUserInputsDTO(running=False)
    # when
    aqt.importing.ImportDialog(mw=MagicMock(), importer=importer)
    # assert
    assert aqt.importing.ImportDialog.exec_.call_count == 0
    monkeypatches.tooltip.assert_called_once_with(monkeypatches.IMPORT_CANCELED_MESSAGE)
    assert importer.initialize_import.call_count == 0