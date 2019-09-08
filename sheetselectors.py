# Qt Dialogs for selecting and naming sheets to import
from PyQt5 import QtCore, QtWidgets

from xsheet import SheetElement

from aqt.qt import *
import aqt

from XmindImport.consts import ICONS_PATH

# TODO: Make a superclass SheetSelector and have both selectors inherit from it

class SingleSheetSelector(QDialog):
    def __init__(self, sheet: SheetElement):
        try:
            self.parent = aqt.mw.app.activeWindow()
        except:
            self.parent = None
        super().__init__(parent=self.parent)
        self.sheet = sheet
        self.build()

    def build(self):
        width = 500
        height = 100
        if not self.parent:
            width *= 2
            height *= 2
        title = self.sheet.getTitle()
        txt = 'Enter name for sheet "' + title + '":'

        self.setWindowTitle('Xmind Import')
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.ico")))
        self.resize(width, height)

        layout = QtWidgets.QWidget(self)
        layout.setGeometry(QtCore.QRect(10, 10, width - 20, height - 20))

        v_layout = QtWidgets.QVBoxLayout(layout)
        v_layout.setContentsMargins(0, 0, 0, 0)

        h_layout_1 = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(layout)
        label.setText(txt)
        h_layout_1.addWidget(label)

        h_layout_2 = QtWidgets.QHBoxLayout()
        user_input = QtWidgets.QLineEdit(layout)
        user_input.setText(title)
        h_layout_2.addWidget(user_input)

        h_layout_3 = QtWidgets.QHBoxLayout()
        buttons = QtWidgets.QDialogButtonBox(layout)
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        h_layout_3.addWidget(buttons)

        v_layout.addLayout(h_layout_1)
        v_layout.addLayout(h_layout_2)
        v_layout.addLayout(h_layout_3)

        frame = self.frameGeometry()
        window_center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())


class MultiSheetSelector(QDialog):
    def __init__(self, sheets):
        try:
            self.parent = aqt.mw.app.activeWindow() or aqt.mw
        except:
            self.parent = None

        super().__init__(parent=self.parent)
        self.sheets = sheets
        self.build()

    def build(self):
        width = 700
        height = 100 + (len(self.sheets) * 24)
        # For Debugging: set size to twice the original size
        if not self.parent:
            width *= 2
            height *= 2
        txt = 'Choose Xmind sheets for import and enter names:'

        self.setWindowTitle('Xmind Import')
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.ico")))
        self.resize(width, height)

        layout = QtWidgets.QWidget(self)
        layout.setGeometry(QtCore.QRect(10, 10, width - 20, height - 20))

        v_layout = QtWidgets.QVBoxLayout(layout)
        v_layout.setContentsMargins(0, 0, 0, 0)

        h_layout_1 = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel(layout)
        label.setText(txt)
        h_layout_1.addWidget(label)

        h_layout_2 = QtWidgets.QHBoxLayout()
        sheet_checkboxes = list()
        sheet_user_inputs = list()
        sheet_v_layout_1 = QtWidgets.QVBoxLayout()
        sheet_v_layout_2 = QtWidgets.QVBoxLayout()
        for sheet in self.sheets:
            title = sheet.getTitle()

            sheet_checkbox = QtWidgets.QCheckBox(layout)
            sheet_checkbox.setText(title)
            sheet_checkboxes.append(sheet_checkbox)
            sheet_v_layout_1.addWidget(sheet_checkbox)

            sheet_user_input = QtWidgets.QLineEdit(layout)
            sheet_user_input.setText(title)
            sheet_user_inputs.append(sheet_user_input)
            sheet_v_layout_2.addWidget(sheet_user_input)
        h_layout_2.addLayout(sheet_v_layout_1)
        h_layout_2.addLayout(sheet_v_layout_2)

        h_layout_3 = QtWidgets.QHBoxLayout()
        buttons = QtWidgets.QDialogButtonBox(layout)
        buttons.setStandardButtons(
            QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Ok)
        h_layout_3.addWidget(buttons)

        v_layout.addLayout(h_layout_1)
        v_layout.addLayout(h_layout_2)
        v_layout.addLayout(h_layout_3)

        # move dialog to center position
        frame = self.frameGeometry()
        window_center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())
