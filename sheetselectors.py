# Qt Dialogs for selecting and naming sheets to import
import os

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QDesktopWidget
from consts import ICONS_PATH

import aqt
from aqt.deckchooser import DeckChooser


class SheetSelector(QDialog):
    def __init__(self, filename):
        self.parent = aqt.mw.app.activeWindow() or aqt.mw
        super().__init__(parent=self.parent)
        self.width = 600
        self.height = 100
        self.deck_text = 'Choose Deck for map "%s":' % filename
        self.deck = None
        self.repair_checkbox = None
        self.running = True
        self.deckId = None
        self.repair = False
        self.tags = dict()

        self.build()

    def build(self):
        return

    def on_ok(self):
        return

    def get_deck_id(self):
        if self.deck:
            return self.deck.selectedId()
        else:
            return 'nodeck'

    def reject(self):
        self.running = False
        super().reject()

    def add_repair_check(self, layout, sheet_layout):
        repair_checkbox = QtWidgets.QCheckBox(layout)
        repair_checkbox.setText('Repair')
        self.repair_checkbox = repair_checkbox
        sheet_layout.addWidget(repair_checkbox)

    def get_inputs(self):
        return {'repair': self.repair, 'deckId': self.deckId,
                'running': self.running}


class DeckSelectionDialog(SheetSelector):
    def __init__(self, sheet_import):
        self.user_input = None
        super().__init__(sheet_import)

    def build(self):
        if not self.parent:
            self.width *= 2
            self.height *= 2
        self.setWindowTitle('Xmind Import')
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.ico")))
        self.resize(self.width, self.height)

        layout = QtWidgets.QWidget(self)
        layout.setGeometry(
            QtCore.QRect(10, 10, self.width - 20, self.height - 20))

        v_layout_1 = QtWidgets.QVBoxLayout(layout)
        v_layout_1.setContentsMargins(0, 0, 0, 0)

        h_layout_1 = QtWidgets.QHBoxLayout()

        v_layout_2 = QtWidgets.QVBoxLayout()
        label_deck = QtWidgets.QLabel(layout)
        label_deck.setText(self.deck_text)
        v_layout_2.addWidget(label_deck)

        v_layout_3 = QtWidgets.QVBoxLayout()
        deckarea = QtWidgets.QWidget(layout)

        self.deck = aqt.deckchooser.DeckChooser(self.parent, deckarea, label=False)
        v_layout_3.addWidget(deckarea)

        h_layout_1.addLayout(v_layout_2)
        h_layout_1.addLayout(v_layout_3)

        h_layout_3 = QtWidgets.QHBoxLayout()
        self.add_repair_check(layout, h_layout_3)

        buttons = QtWidgets.QDialogButtonBox(layout)
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        h_layout_3.addWidget(buttons)

        v_layout_1.addLayout(h_layout_1)
        v_layout_1.addLayout(h_layout_3)

        frame = self.frameGeometry()
        window_center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())

        buttons.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(self.on_ok)
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(self.reject)

    def on_ok(self):
        self.deckId = self.get_deck_id()
        self.repair = self.repair_checkbox.isChecked()
        self.accept()
