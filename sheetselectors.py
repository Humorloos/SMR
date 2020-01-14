# Qt Dialogs for selecting and naming sheets to import
from PyQt5 import QtCore, QtWidgets

from aqt.qt import *
from aqt.deckchooser import DeckChooser
import aqt

from .consts import ICONS_PATH


class SheetSelector(QDialog):
    def __init__(self, filename):
        try:
            self.parent = aqt.mw.app.activeWindow() or aqt.mw
        except:
            self.parent = None
        super().__init__(parent=self.parent)
        self.width = 600
        self.height = 100
        self.deck_text = 'Choose Deck for map "%s":' % filename
        self.deck = None
        self.repairCheckbox = None
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

    def addRepairCheck(self, layout, sheetLayout):
        repairCheckbox = QtWidgets.QCheckBox(layout)
        repairCheckbox.setText('Repair')
        self.repairCheckbox = repairCheckbox
        sheetLayout.addWidget(repairCheckbox)

    def getInputs(self):
        return {'repair': self.repair, 'deckId': self.deckId,
                'running': self.running}


class SingleSheetSelector(SheetSelector):
    def __init__(self, sheetImport):
        self.user_input = None
        super().__init__(sheetImport)

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
        try:
            self.deck = aqt.deckchooser.DeckChooser(
                self.parent, deckarea, label=False)
        except:
            self.deck = None
        v_layout_3.addWidget(deckarea)

        h_layout_1.addLayout(v_layout_2)
        h_layout_1.addLayout(v_layout_3)

        h_layout_3 = QtWidgets.QHBoxLayout()
        self.addRepairCheck(layout, h_layout_3)

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

        buttons.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            self.on_ok)
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(
            self.reject)

    def on_ok(self):
        self.deckId = self.get_deck_id()
        self.repair = self.repairCheckbox.isChecked()
        self.accept()


class MultiSheetSelector(SheetSelector):
    def __init__(self, sheets):
        self.sheet_checkboxes = dict()
        self.sheet_user_inputs = dict()
        super().__init__(sheets)

    def build(self):
        self.height += ((len(self.sheets) + 2) * 20)
        # For Debugging: set size to twice the original size
        if not self.parent:
            self.width *= 2
            self.height *= 2
        sheet_text = 'Choose Xmind sheets for import and enter names:'

        self.setWindowTitle('Xmind Import')
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.ico")))
        self.resize(self.width, self.height)

        layout = QtWidgets.QWidget(self)
        layout.setGeometry(QtCore.QRect(
            10, 10, self.width - 20, self.height - 20))

        v_layout = QtWidgets.QVBoxLayout(layout)
        v_layout.setContentsMargins(0, 0, 0, 0)

        h_layout_deck = QtWidgets.QHBoxLayout()
        label_deck = QtWidgets.QLabel(layout)
        label_deck.setText(self.deck_text)
        h_layout_deck.addWidget(label_deck)
        deckarea = QtWidgets.QWidget(layout)
        try:
            self.deck = aqt.deckchooser.DeckChooser(
                self.parent, deckarea, label=False)
        except:
            self.deck = None
        h_layout_deck.addWidget(deckarea)

        h_layout_sheet_text = QtWidgets.QHBoxLayout()
        label_text = QtWidgets.QLabel(layout)
        label_text.setText(sheet_text)
        h_layout_sheet_text.addWidget(label_text)

        h_layout_sheets = QtWidgets.QHBoxLayout()
        sheet_v_layout_1 = QtWidgets.QVBoxLayout()
        sheet_v_layout_2 = QtWidgets.QVBoxLayout()

        for sheet_title in self.sheets:
            title = sheet_title

            sheet_checkbox = QtWidgets.QCheckBox(layout)
            sheet_checkbox.setText(title)
            self.sheet_checkboxes[sheet_title] = sheet_checkbox

            sheet_v_layout_1.addWidget(sheet_checkbox)
            sheet_user_input = QtWidgets.QLineEdit(layout)
            sheet_user_input.setText(title)
            self.sheet_user_inputs[sheet_title] = sheet_user_input

            sheet_v_layout_2.addWidget(sheet_user_input)
        h_layout_sheets.addLayout(sheet_v_layout_1)
        h_layout_sheets.addLayout(sheet_v_layout_2)

        h_layout_3 = QtWidgets.QHBoxLayout()
        self.addRepairCheck(layout, h_layout_3)

        buttons = QtWidgets.QDialogButtonBox(layout)
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        h_layout_3.addWidget(buttons)

        v_layout.addLayout(h_layout_deck)
        v_layout.addLayout(h_layout_sheet_text)
        v_layout.addLayout(h_layout_sheets)
        v_layout.addLayout(h_layout_3)

        # move dialog to center position
        frame = self.frameGeometry()
        window_center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())

        buttons.button(QtWidgets.QDialogButtonBox.Ok).clicked.connect(
            self.on_ok)
        buttons.button(QtWidgets.QDialogButtonBox.Cancel).clicked.connect(
            self.reject)

    def on_ok(self):
        self.sheets = list()
        self.deckId = self.get_deck_id()
        self.repair = self.repairCheckbox.isChecked()
        for sheet_title in self.sheet_checkboxes:
            if self.sheet_checkboxes[sheet_title].isChecked():
                self.tags[sheet_title] = self.getTag(
                    self.sheet_user_inputs[sheet_title].text())
                self.sheets.append(sheet_title)
        self.accept()
