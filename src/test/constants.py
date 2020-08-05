import os

from main.consts import ADDON_PATH
from main.dto.nodecontentdto import NodeContentDTO

SUPPORT_PATH = os.path.join(ADDON_PATH, 'src', 'test', 'support')
SMR_WORLD_PATH = os.path.join(SUPPORT_PATH, "smr_world")
SMR_WORLD_CSV_PATH = os.path.join(SMR_WORLD_PATH, "csv")
EMPTY_SMR_WORLD_NAME = "empty_smr_world.sqlite3"
TEST_COLLECTIONS_PATH = os.path.join(SUPPORT_PATH, 'collections')
EMPTY_COLLECTION_PATH_SESSION = os.path.join(TEST_COLLECTIONS_PATH, 'empty_smr_col_session/empty_smr_col_session.anki2')
EMPTY_COLLECTION_PATH_FUNCTION = os.path.join(TEST_COLLECTIONS_PATH,
                                              'empty_smr_col_function', 'empty_smr_col_function.anki2')
EXAMPLE_MAP_PATH = os.path.join(ADDON_PATH, 'resources', 'example map.xmind')
ABSENT_XMIND_FILE_PATH = os.path.join(SUPPORT_PATH, 'absent_file.xmind')
EXAMPLE_MAP_N_EDGES = 28
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

# edges from smr_world
PRONOUNCIATION_EDGE_XMIND_ID = "4s27e1mvsb5jqoiuaqmnlo8m71"
EDGE_WITH_MEDIA_XMIND_ID = "7ite3obkfmbcasdf12asd123ga"
EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID = "61irckf1nloq42brfmbu0ke92v"
EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID = "6iivm8tpoqj2c0euaabtput14l"
# edge from xmind test file
TYPES_EDGE_XMIND_ID = '485fcs7jl72gtqesace4v8igf0'

# nodes
NEUROTRANSMITTERS_XMIND_ID = "4r6avbt0pbuam4fg07jod0ubec"
MEDIA_HYPERLINK_XMIND_ID = '1s7h0rvsclrnvs8qq9u71acml5'
NEUROTRANSMITTERS_NODE_CONTENT = NodeContentDTO(image='attachments/629d18n2i73im903jkrjmr98fg.png',
                                                title='neurotransmitters')
MEDIA_HYPERLINK_NODE_CONTENT = NodeContentDTO(
    media="C:/Users/lloos/OneDrive - bwedu/Projects/AnkiAddon/anki-addon-dev/addons21/XmindImport/resources"
          "/serotonin.mp3")
MEDIA_ATTACHMENT_NODE_CONTENT: NodeContentDTO = NodeContentDTO(media='attachments/395ke7i9a6nkutu85fcpa66as2.mp4')
NEUROTRANSMITTERS_CLASS_NAME = 'neurotransmittersximage_629d18n2i73im903jkrjmr98fg_extension_png'
EMPTY_NODE_TAG_ID = "6b0ho6vvcs4pcacchhsgju7513"

EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE = \
    b'\x80\x04\x95\xff\x02\x00\x00\x00\x00\x00\x00\x8c\x16anki.importing.noteimp\x94\x8c\x0bForeignNote\x94\x93\x94' \
    b')\x81\x94}\x94(\x8c\x06fields\x94]\x94(\x8c\xc1biological psychology<li>investigates: information transfer and ' \
    b'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: dopamine,adrenaline,Serotonin,' \
    b'noradrenaline</li>\x94\x8c\x03are\x94\x8c\x0fbiogenic ' \
    b'amines\x94\x8c\x00\x94h\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\n\x8c\t|{|{{{|\x7f{' \
    b'\x94e\x8c\x04tags\x94]\x94(\x8c& ::example_map::biological_psychology ' \
    b'\x94\x8c\x1a6iivm8tpoqj2c0euaabtput14l\x94e\x8c\x04deck\x94N\x8c\x05cards\x94}\x94K\x01h\x00\x8c\x0bForeignCard' \
    b'\x94\x93\x94)\x81\x94}\x94(\x8c\x03due\x94K\x00\x8c\x03ivl\x94K\x01\x8c\x06factor\x94M\xc4\t\x8c\x04reps\x94K' \
    b'\x00\x8c\x06lapses\x94K\x00ubs\x8c\tfieldsStr\x94\x8c\xf2biological psychology<li>investigates: information ' \
    b'transfer and processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: dopamine,' \
    b'adrenaline,Serotonin,noradrenaline</li>\x1fare\x1fbiogenic ' \
    b'amines\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f|{|{{{|\x7f{\x94ub.'

EDGE_FOLLOWING_MULTIPLE_NODES_NOTE_ID = 12345
