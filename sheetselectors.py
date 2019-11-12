# Qt Dialogs for selecting and naming sheets to import
from PyQt5 import QtCore, QtWidgets

from aqt.qt import *
from aqt.deckchooser import DeckChooser
import aqt

from .consts import ICONS_PATH

class SheetSelector(QDialog):
    def __init__(self, sheets, topic):
        try:
            self.parent = aqt.mw.app.activeWindow() or aqt.mw
        except:
            self.parent = None
        super().__init__(parent=self.parent)
        self.sheets = list()
        for sheet in sheets:
            sheetImport = dict(sheet=sheet, tag="", deckId="")
            self.sheets.append(sheetImport)
        self.topic = topic
        self.width = 600
        self.height = 100
        self.deck_text = 'Choose Deck:'
        self.deck = None
        self.repairCheckbox = None
        self.running = True

        self.build()



    def build(self):
        return

    def on_ok(self):
        return

    def getTag(self, userInput):
        return " " + (self.deck.deckName() + '_' + userInput).replace(" ",
                                                                      "_") + " "

    def reject(self):
        self.running = False
        super().reject()

    def addRepairCheck(self, layout, sheetLayout):
        repairCheckbox = QtWidgets.QCheckBox(layout)
        repairCheckbox.setText('Repair')
        self.repairCheckbox = repairCheckbox
        sheetLayout.addWidget(repairCheckbox)

class SingleSheetSelector(SheetSelector):
    def __init__(self, sheets, topic):
        self.user_input = None
        super().__init__(sheets, topic)

    def build(self):
        if not self.parent:
            self.width *= 2
            self.height *= 2
        title = self.sheets[0]['sheet'].getTitle()
        tag_text = 'Enter name for sheet "' + title + '":'
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
        label_tag = QtWidgets.QLabel(layout)
        label_tag.setText(tag_text)
        v_layout_2.addWidget(label_tag)

        v_layout_3 = QtWidgets.QVBoxLayout()
        deckarea = QtWidgets.QWidget(layout)
        try:
            self.deck = aqt.deckchooser.DeckChooser(
                self.parent, deckarea, label=False)
        except:
            self.deck = None
        v_layout_3.addWidget(deckarea)
        self.user_input = QtWidgets.QLineEdit(layout)
        self.user_input.setText(title)
        v_layout_3.addWidget(self.user_input)

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
        self.sheets[0]['tag'] = self.getTag(self.user_input.text())
        self.sheets[0]['deckId'] = self.deck.selectedId()
        self.sheets[0]['repair'] = self.repairCheckbox.isChecked()
        self.accept()


class MultiSheetSelector(SheetSelector):
    def __init__(self, sheets, topic):
        self.sheet_checkboxes = list()
        self.sheet_user_inputs = list()
        super().__init__(sheets, topic)

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

        for sheet in self.sheets:
            title = sheet['sheet'].title.text

            sheet_checkbox = QtWidgets.QCheckBox(layout)
            sheet_checkbox.setText(title)
            self.sheet_checkboxes.append(sheet_checkbox)
            sheet_v_layout_1.addWidget(sheet_checkbox)

            sheet_user_input = QtWidgets.QLineEdit(layout)
            sheet_user_input.setText(title)
            self.sheet_user_inputs.append(sheet_user_input)
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
        new_sheets = list()
        for box_id, box in enumerate(self.sheet_checkboxes, start=0):
            if box.isChecked():
                new_sheet = self.sheets[box_id]
                new_sheet['tag'] = self.getTag(
                    self.sheet_user_inputs[box_id].text())
                new_sheet['deckId'] = self.deck.selectedId()
                new_sheet['repair'] = self.repairCheckbox.isChecked()
                new_sheets.append(new_sheet)
        self.sheets = new_sheets
        self.accept()
