import os

from consts import ADDON_PATH

from anki import Collection

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')
EMPTY_COLLECTION_PATH = os.path.join(SUPPORT_PATH, 'empty_smr_col.anki2')
EMPTY_COLLECTION = Collection(EMPTY_COLLECTION_PATH)
