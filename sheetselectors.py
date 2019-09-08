# Qt Dialogs for selecting and naming sheets to import
from PyQt5 import QtCore, QtWidgets

from xsheet import SheetElement

from aqt.qt import *
import aqt

from XmindImport.consts import ICONS_PATH



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
        self.setWindowIcon(QIcon(os.path.join(ICONS_PATH, "icon.png")))
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
        center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())
