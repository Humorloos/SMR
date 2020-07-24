import os

from main.consts import ADDON_PATH
from main.dto.nodecontentdto import NodeContentDTO

SUPPORT_PATH = os.path.join(ADDON_PATH, 'src', 'test', 'support')
SMR_WORLD_PATH = os.path.join(SUPPORT_PATH, "smr_world")
SMR_WORLD_CSV_PATH = os.path.join(SMR_WORLD_PATH, "csv")
EMPTY_COLLECTION_PATH = os.path.join(SUPPORT_PATH, 'empty_smr_col.anki2')
EXAMPLE_MAP_PATH = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
TEST_DECK_ID = "12345"
TEST_FILE_PATH = "path for test file"
TEST_CONCEPT_STORID = 153
TEST_CONCEPT_CLASS_NAME = "test_concept"
TEST_CONCEPT_NODE_ID = "node id"
TEST_CONCEPT_2_NODE_ID = "node id2"
TEST_CONCEPT_2_STORID = 155
TEST_CONCEPT_2_CLASS_NAME = "test_concept2"
TEST_RELATION_STORID = 154
TEST_RELATION_CLASS_NAME = "test_relation"
TEST_RELATION_EDGE_ID = "edge id"
TEST_SHEET_ID = "sheet id"
TYPES_EDGE_XMIND_ID = '485fcs7jl72gtqesace4v8igf0'
NEUROTRANSMITTERS_XMIND_ID = "4r6avbt0pbuam4fg07jod0ubec"
NEUROTRANSMITTERS_NODE_CONTENT = NodeContentDTO(image='attachments/629d18n2i73im903jkrjmr98fg.png',
                                                title='neurotransmitters')
NEUROTRANSMITTERS_CLASS_NAME = 'neurotransmittersximage_629d18n2i73im903jkrjmr98fg_extension_png'
EMPTY_NODE_TAG_ID = "6b0ho6vvcs4pcacchhsgju7513"
