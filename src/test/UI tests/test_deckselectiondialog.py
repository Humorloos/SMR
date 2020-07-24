import sys
from unittest.mock import MagicMock, Mock

from PyQt5 import QtWidgets

from aqt import AnkiQt
import main.deckselectiondialog
from PyQt5.QtWidgets import QWidget, QDialog

import aqt
import aqt.deckchooser


def test_deck_selection_dialog(mocker):
    """
    Simple UI test for deck selection dialog
    """
    # app is necessary for Qt Widgets to work
    # noinspection PyUnusedLocal
    app = QtWidgets.QApplication(sys.argv)
    # given
    filename = 'example_map.xmind'
    test_id = "my id"
    mocker.patch.object(aqt.deckchooser, "DeckChooser")
    aqt.deckchooser.DeckChooser.return_value = aqt.deckchooser.DeckChooser
    aqt.deckchooser.DeckChooser.selectedId.return_value = test_id
    mocker.patch("aqt.mw")
    aqt.mw.app.activeWindow.return_value = QWidget()
    mocker.patch('main.deckselectiondialog.DeckSelectionDialog.exec_')    # disable to show the widget
    cut = main.deckselectiondialog.DeckSelectionDialog(mw=QWidget(), filename=filename)
    # when
    cut.accept()

    # then
    assert cut._deck_id == test_id
