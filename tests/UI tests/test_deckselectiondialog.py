import sys

from PyQt5 import QtWidgets
import deckselectiondialog
from PyQt5.QtWidgets import QWidget

import aqt
import aqt.deckchooser


def test_deck_selection_dialog(mocker):
    """
    Simple UI test for deck selection dialog
    """
    app = QtWidgets.QApplication(sys.argv)
    # given
    filename = 'example_map.xmind'
    test_id = "my id"

    # Mock deckchooser
    mocker.patch.object(aqt.deckchooser, "DeckChooser")
    aqt.deckchooser.DeckChooser.return_value = aqt.deckchooser.DeckChooser
    aqt.deckchooser.DeckChooser.selectedId.return_value = test_id

    # Mock mw
    mocker.patch("aqt.mw")
    aqt.mw.app.activeWindow.return_value = QWidget()

    cut = deckselectiondialog.DeckSelectionDialog(filename)

    # # For checking out the widget's design:
    # cut.show()
    # app.exec()

    # when
    cut.accept()

    # then
    assert cut.deckId == test_id
