import os

from consts import ADDON_PATH

from anki import Collection

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')
SMR_WORLD_PATH = os.path.join(SUPPORT_PATH, "smr_world")
SMR_WORLD_CSV_PATH = os.path.join(SMR_WORLD_PATH, "csv")
EMPTY_COLLECTION_PATH = os.path.join(SUPPORT_PATH, 'empty_smr_col.anki2')
EMPTY_COLLECTION = Collection(EMPTY_COLLECTION_PATH)
EXAMPLE_MAP_PATH = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
TEST_DECK_ID = "12345"
TEST_FILE_PATH = "path for test file"
TEST_CONCEPT_STORID = 153
TEST_CONCEPT_CLASS_NAME = "test_concept"
TEST_SHEET_ID = "sheet id"
TYPES_EDGE_XMIND_ID = '485fcs7jl72gtqesace4v8igf0'
NEUROTRANSMITTERS_XMIND_ID = "4r6avbt0pbuam4fg07jod0ubec"
NEUROTRANSMITTERS_NODE_CONTENT = {'content': 'neurotransmitters',
                                  'media': {'image': 'attachments/629d18n2i73im903jkrjmr98fg.png', 'media': None}}
NEUROTRANSMITTERS_CLASS_NAME = 'neurotransmittersximage_629d18n2i73im903jkrjmr98fg_extension_png'
EMPTY_NODE_TAG_ID = "6b0ho6vvcs4pcacchhsgju7513"
