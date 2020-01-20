import json

from anki.utils import splitFields

from .utils import *


def meta_from_flds(flds):
    return json.loads(splitFields(flds)[-1])


class XNoteManager():
    def __init__(self, col):
        self.col = col

    def get_xmind_files(self):
        model = xModelId(self.col)
        return set(meta_from_flds(flds[0])['path'] for flds in
                   self.col.db.execute(
                       'select flds from notes where mid = %s' % model))


