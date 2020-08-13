import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDesktopWidget, QMessageBox

import smr.consts as cts
from qt.aqt import AnkiQt


class SmrWorldMigrationDialog(QMessageBox):
    """
    Message box for instructions concerning update to version 0.1.0 with migration to smr world
    """
    def __init__(self, mw: AnkiQt):

        self.parent = mw
        super().__init__(parent=self.parent)
        self.setWindowIcon(QIcon(os.path.join(cts.ICONS_PATH, "icon.ico")))
        self.setWindowTitle('Stepwise Map Retrieval addon update to version ' + cts.SMR_CONFIG['version'])
        self.setMinimumWidth(600)
        self.SUCCESSFUL_MIGRATION_REQUIREMENTS = \
            'For the update to be successful, please make sure that all of your imported xmind files are stored at ' \
            'the same place where they were when you last imported them. '
        self.setText(
            'This update will make tags assigned to your concept maps compatible with the addon "hierarchical tags". '
            'Stepwise Map Retrieval will now match answers with the same content during review and considers them '\
            'in the review order.\n\n' +
            self.SUCCESSFUL_MIGRATION_REQUIREMENTS +
            '\n\nDue to the automatic recognition of crosslinks, this addon will not recognize hyperlinks '
            'in maps anymore. If you want to include crosslinks in your concept map, you need to use concepts with '
            'the same content now. For further explanations, refer to <link missing>')
        self.setStandardButtons(self.Cancel)
        self.start_update_button = self.addButton("Start Update", self.YesRole)
        self.setIcon(self.Question)

        # Display the message box in the center of the screen
        frame = self.frameGeometry()
        window_center = QDesktopWidget().availableGeometry().center()
        frame.moveCenter(window_center)
        self.move(frame.topLeft())
