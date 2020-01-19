from .xmanager import XManager
from .xnotemanager import XNoteManager


class XSyncer():
    def __init__(self, col):
        self.col = col

        self.note_manager = XNoteManager(col=col)
        xmind_files = self.note_manager.get_xmind_files()
        self.map_managers = [XManager(f) for f in xmind_files]
        print()

    def run(self):
        print()