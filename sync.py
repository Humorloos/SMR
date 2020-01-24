import os

from .xmanager import XManager, remote_file
from .xnotemanager import XNoteManager
from .statusmanager import StatusManager


# Algorithm for synchronization was adopted from
# https://unterwaditzer.net/2016/sync-algorithm.html
class XSyncer():
    def __init__(self, col, status_file=None):
        self.col = col

        self.note_manager = XNoteManager(col=col)
        self.xmind_files = self.note_manager.get_xmind_files()
        # self.map_managers = [XManager(f) for f in self.xmind_files]
        self.status_manager = StatusManager(status_file=status_file)

    def run(self):
        local = {f: self.note_manager.get_local(f) for f in self.xmind_files}
        remote_files = {f: remote_file(f) for f in self.xmind_files}
        status = {d['file']: d for d in self.status_manager.status}
        for f in self.xmind_files:
            local_change = status[f]['ankiMod'] != local[f]['ankiMod']
            remote_change = status[f]['xMod'] != remote_files[f]['xMod']
            if not local_change and not remote_change:
                pass
            elif local_change and not remote_change:
                print('')
            elif not local_change and remote_change:
                print('')
            else:
                print('')

    def process_local_change(self):
        print('')