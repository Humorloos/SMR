import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget

from smr.ui.smrworldmigrationdialog import SmrWorldMigrationDialog


def test_smr_world_migration_dialog():
    """
    Simple UI test for deck selection dialog
    """
    # app is necessary for Qt Widgets to work
    # noinspection PyUnusedLocal
    app = QtWidgets.QApplication(sys.argv)
    cut = SmrWorldMigrationDialog(mw=QWidget())
    # enable to show dialog
    # result = cut.exec()
    assert True
