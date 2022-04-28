# Qt Dialogs for selecting and naming sheets to import
import os
from typing import Optional

from PyQt6 import QtWidgets
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QWidget
from aqt import AnkiQt
import aqt
from aqt.deckchooser import DeckChooser

from ..consts import ICONS_PATH
from ..dto.deckselectiondialoguserinputsdto import DeckSelectionDialogUserInputsDTO


class DeckSelectionDialog(QDialog):
    def __init__(self, mw: AnkiQt, filename: str):
        self.user_input = None
        self.parent = mw
        super().__init__(parent=self.parent)
        self.width = 600
        self.height = 100
        self.deck_text = 'Choose Deck for map "%s":' % filename
        self.deck = None
        self.repair_checkbox = None
        self._running = True
        self._deck_id: Optional[int] = None
        self._deck_name: str = ''
        self._repair = False
        self.tags = dict()
        self._build()
        self.exec()

    def reject(self):
        self._running = False
        super().reject()

    def accept(self):
        self._deck_id = self.deck.selectedId()
        self._deck_name = self.deck.deckName()
        self._repair = self.repair_checkbox.isChecked()
        super().accept()

    def get_inputs(self) -> DeckSelectionDialogUserInputsDTO:
        return DeckSelectionDialogUserInputsDTO(repair=self._repair, deck_id=self._deck_id, deck_name=self._deck_name, running=self._running)

    def _build(self) -> None:
        """
        Builds the dialog from individual widgets and positions it
        """
        self.setWindowTitle('Xmind Import')
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.ico")))
        self.resize(self.width, self.height)

        widget = QWidget(self)
        widget.setGeometry(QRect(10, 10, self.width - 20, self.height - 20))

        col_1 = QtWidgets.QVBoxLayout(widget)
        col_1.setContentsMargins(0, 0, 0, 0)

        col_1_row_1 = QtWidgets.QHBoxLayout()

        col_1_row_1_col_1 = QtWidgets.QVBoxLayout()
        label_deck = QtWidgets.QLabel(widget)
        label_deck.setText(self.deck_text)
        col_1_row_1_col_1.addWidget(label_deck)

        col_1_row_1_col_2 = QtWidgets.QVBoxLayout()
        deckarea = QtWidgets.QWidget(widget)

        self.deck = aqt.deckchooser.DeckChooser(self.parent, deckarea, label=False)
        col_1_row_1_col_2.addWidget(deckarea)

        col_1_row_1.addLayout(col_1_row_1_col_1)
        col_1_row_1.addLayout(col_1_row_1_col_2)

        col_1_row_2 = QtWidgets.QHBoxLayout()

        # Add the checkbox element for indicating whether to use the import to repair the xmind file
        repair_checkbox = QtWidgets.QCheckBox(widget)
        repair_checkbox.setText('Repair')
        self.repair_checkbox = repair_checkbox
        col_1_row_2.addWidget(repair_checkbox)

        buttons = QtWidgets.QDialogButtonBox(widget)
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.StandardButton.Cancel | QtWidgets.QDialogButtonBox.StandardButton.Ok)
        col_1_row_2.addWidget(buttons)

        col_1.addLayout(col_1_row_1)
        col_1.addLayout(col_1_row_2)

        frame = self.frameGeometry()
        window_center = self.screen().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())

        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
