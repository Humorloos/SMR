from unittest.mock import MagicMock

import aqt.importing
import main.monkeypatches
from main.dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO


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