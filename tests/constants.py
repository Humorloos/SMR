import os

from smr.consts import ADDON_PATH
from smr.dto.nodecontentdto import NodeContentDto
from smr.dto.xmindfiledto import XmindFileDto
from smr.dto.xmindnodedto import XmindNodeDto
from smr.xnotemanager import FieldTranslator

SUPPORT_PATH = os.path.join(ADDON_PATH, 'tests', 'support')
SMR_WORLD_PATH = os.path.join(SUPPORT_PATH, "smr_world")
SMR_WORLD_CSV_PATH = os.path.join(SMR_WORLD_PATH, "csv")
ORIGINAL_SMR_WORLD_WITH_EXAMPLE_MAP_PATH = os.path.join(SMR_WORLD_PATH, "smr_world_with_example_map",
                                                        "smr_world.sqlite3")
EMPTY_SMR_WORLD_NAME = "empty_smr_world.sqlite3"

# collections
TEST_COLLECTIONS_DIRECTORY = os.path.join(SUPPORT_PATH, 'collections')
# empty collections
# session
TEMPORARY_EMPTY_COLLECTION_SESSION_PATH = os.path.join(TEST_COLLECTIONS_DIRECTORY, 'temporary_empty_smr_col_session',
                                                       'empty_smr_col_session.anki2')
# function
TEMPORARY_EMPTY_COLLECTION_FUNCTION_NAME = 'empty_smr_col_function'
TEMPORARY_EMPTY_COLLECTION_FUNCTION_DIRECTORY = os.path.join(TEST_COLLECTIONS_DIRECTORY,
                                                             'temporary_empty_smr_col_function')
TEMPORARY_EMPTY_COLLECTION_FUNCTION_PATH = os.path.join(TEMPORARY_EMPTY_COLLECTION_FUNCTION_DIRECTORY,
                                                        TEMPORARY_EMPTY_COLLECTION_FUNCTION_NAME + '.anki2')
TEMPORARY_EMPTY_COLLECTION_FUNCTION_MEDIA = os.path.join(TEMPORARY_EMPTY_COLLECTION_FUNCTION_DIRECTORY,
                                                         TEMPORARY_EMPTY_COLLECTION_FUNCTION_NAME + '.media')
# collections with example map
# no changes
DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY = os.path.join(TEST_COLLECTIONS_DIRECTORY,
                                                             'default_collection_with_example_map')
DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_NAME = 'collection'
DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_PATH = os.path.join(DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY,
                                                        DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_NAME + '.anki2')
DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_MEDIA = os.path.join(DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY,
                                                         DEFAULT_COLLECTION_WITH_EXAMPLE_MAP_NAME + '.media')
# with changes
# default
DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY = os.path.join(TEST_COLLECTIONS_DIRECTORY,
                                                                     'default_changed_collection_with_example_map')
DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME = 'collection'
DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH = os.path.join(
    DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY, DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME + '.anki2')
DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA = os.path.join(
    DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY, DEFAULT_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME + '.media')
# temporary
TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY = os.path.join(TEST_COLLECTIONS_DIRECTORY,
                                                                       "temporary_changed_collection_with_example_map")
TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME = "changed_col_with_example_map"
TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH = os.path.join(
    TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY,
    TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME + ".anki2")
TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA = os.path.join(
    TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_DIRECTORY,
    TEMPORARY_CHANGED_COLLECTION_WITH_EXAMPLE_MAP_NAME + ".media")
# Collection version 0.0.1 for migration
ORIGINAL_COLLECTION_VERSION_001_PATH = os.path.join(TEST_COLLECTIONS_DIRECTORY, 'original_collection_version_0.0.1',
                                                    'collection.anki2')

NEW_IMAGE_NAME = "paste-cbf726a37a2fa4c403412f84fd921145335bd0b0.jpg"
NEUROTRANSMITTERS_IMAGE_XMIND_URI = "attachments/09r2e442o8lppjfeblf7il2rmd.png"
NEUROTRANSMITTERS_IMAGE_ANKI_FILE_NAME = "attachments09r2e442o8lppjfeblf7il2rmd.png"
RESOURCES_PATH = os.path.join(ADDON_PATH, 'resources')
# maps
MAPS_DIRECTORY = os.path.join(SUPPORT_PATH, 'maps')
DEFAULT_MAPS_DIRECTORY = os.path.join(MAPS_DIRECTORY, 'no_changes')
CHANGED_MAPS_DIRECTORY = os.path.join(MAPS_DIRECTORY, 'changes')
TEMPORARY_MAPS_DIRECTORY = os.path.join(MAPS_DIRECTORY, 'temporary')
EXAMPLE_MAP_NAME = "example map"
ORIGINAL_EXAMPLE_MAP_PATH = os.path.join(RESOURCES_PATH, EXAMPLE_MAP_NAME + '.xmind')
DEFAULT_EXAMPLE_MAP_PATH = os.path.join(DEFAULT_MAPS_DIRECTORY, EXAMPLE_MAP_NAME + '.xmind')
TEMPORARY_EXAMPLE_MAP_PATH = os.path.join(TEMPORARY_MAPS_DIRECTORY, EXAMPLE_MAP_NAME + '.xmind')
GENERAL_PSYCHOLOGY_MAP_NAME = 'example_general_psychology'
ORIGINAL_GENERAL_PSYCHOLOGY_MAP_PATH = os.path.join(RESOURCES_PATH, GENERAL_PSYCHOLOGY_MAP_NAME + '.xmind')
DEFAULT_GENERAL_PSYCHOLOGY_MAP_PATH = os.path.join(DEFAULT_MAPS_DIRECTORY, GENERAL_PSYCHOLOGY_MAP_NAME + '.xmind')
TEMPORARY_GENERAL_PSYCHOLOGY_MAP_PATH = os.path.join(TEMPORARY_MAPS_DIRECTORY, GENERAL_PSYCHOLOGY_MAP_NAME + '.xmind')
HYPERLINK_MEDIA_NAME = "serotonin.mp3"
ORIGINAL_HYPERLINK_MEDIA_PATH = os.path.join(RESOURCES_PATH, HYPERLINK_MEDIA_NAME)
DEFAULT_HYPERLINK_MEDIA_PATH = os.path.join(DEFAULT_MAPS_DIRECTORY, HYPERLINK_MEDIA_NAME)
TEMPORARY_HYPERLINK_MEDIA_PATH = os.path.join(TEMPORARY_MAPS_DIRECTORY, HYPERLINK_MEDIA_NAME)

CONTENT_NAME = 'content.xml'
CONTENT_PATH = os.path.join(MAPS_DIRECTORY, CONTENT_NAME)

ABSENT_XMIND_FILE_PATH = os.path.join(SUPPORT_PATH, 'absent_file.xmind')
EXAMPLE_MAP_N_EDGES = 34

# values from smr world for tests
# xmind files
TEST_FILE_DIRECTORY = "mypath"
TEST_FILE_NAME = "test_file"
TEST_FILE_MAP_LAST_MODIFIED = 1594823958217
TEST_FILE_FILE_LAST_MODIFIED = 1594823958.8585837
TEST_DECK_ID = 1579442668731
TEST_XMIND_FILE = XmindFileDto(directory=TEST_FILE_DIRECTORY, file_name=TEST_FILE_NAME,
                               map_last_modified=TEST_FILE_MAP_LAST_MODIFIED,
                               file_last_modified=TEST_FILE_FILE_LAST_MODIFIED, deck_id=TEST_DECK_ID)
# xmind sheets
TEST_SHEET_ID = "sheet id"
# xmind edges
TEST_RELATION_EDGE_ID = "edge id"
TEST_EDGE_TITLE = 'edge title'
TEST_EDGE_IMAGE = 'edge image'
TEST_EDGE_MEDIA = 'edge media'
TEST_RELATION_STORID = 154
TEST_EDGE_LAST_MODIFIED = 1578313461243
TEST_EDGE_ORDER_NUMBER = 1
TEST_XMIND_EDGE = XmindNodeDto(node_id=TEST_RELATION_EDGE_ID, sheet_id=TEST_SHEET_ID, title=TEST_EDGE_TITLE,
                               image=TEST_EDGE_IMAGE, link=TEST_EDGE_MEDIA, ontology_storid=TEST_RELATION_STORID,
                               last_modified=TEST_EDGE_LAST_MODIFIED, order_number=TEST_EDGE_ORDER_NUMBER)
# xmind nodes
TEST_CONCEPT_NODE_ID = "node id"
TEST_NODE_TITLE = 'node title'
TEST_NODE_IMAGE = 'node image'
TEST_NODE_MEDIA = 'node media'
TEST_CONCEPT_STORID = 153
TEST_NODE_LAST_MODIFIED = 1578314907411
TEST_NODE_ORDER_NUMBER = 1
TEST_XMIND_NODE = XmindNodeDto(node_id=TEST_CONCEPT_NODE_ID, sheet_id=TEST_SHEET_ID, title=TEST_NODE_TITLE,
                               image=TEST_NODE_IMAGE, link=TEST_NODE_MEDIA, ontology_storid=TEST_CONCEPT_STORID,
                               last_modified=TEST_NODE_LAST_MODIFIED, order_number=TEST_NODE_ORDER_NUMBER)
TEST_FILE_PATH = os.path.join(TEST_FILE_DIRECTORY, TEST_FILE_NAME + '.xmind')
TEST_CONCEPT_CLASS_NAME = "test_concept"
TEST_CONCEPT_2_NODE_ID = "node id2"
TEST_CONCEPT_2_STORID = 155
TEST_CONCEPT_2_CLASS_NAME = "test_concept2"
TEST_RELATION_CLASS_NAME = "test_relation"

# edges from smr_world
EDGE_WITH_MEDIA_XMIND_ID = "7ite3obkfmbcasdf12asd123ga"
EDGE_PRECEDING_MULTIPLE_NODES_XMIND_ID = "61irckf1nloq42brfmbu0ke92v"
EDGE_FOLLOWING_MULTIPLE_NODES_XMIND_ID = "6iivm8tpoqj2c0euaabtput14l"
# edge from xmind test file
TYPES_EDGE_ID = '485fcs7jl72gtqesace4v8igf0'
EXAMPLE_IMAGE_EDGE_ID = '08eq1rdricsp1nt1b7aa181sq4'
PRONOUNCIATION_EDGE_ID = "4s27e1mvsb5jqoiuaqmnlo8m71"
CONSIST_OF_EDGE_ID = '0eaob1gla0j1qriki94n2os9oe'

# nodes
NEUROTRANSMITTERS_XMIND_ID = "4r6avbt0pbuam4fg07jod0ubec"
MEDIA_HYPERLINK_XMIND_ID = '1s7h0rvsclrnvs8qq9u71acml5'
ONE_OR_MORE_AMINE_GROUPS_NODE_ID = '0s0is5027b7r6akh3he0nbu478'
ENZYMES_NODE_ID = '5e2cicue01ikp5vnq5pp46np83'
NEUROTRANSMITTERS_NODE_CONTENT = NodeContentDto(image='attachments/629d18n2i73im903jkrjmr98fg.png',
                                                title='neurotransmitters')
# Media hyperlink path as saved in content.xml, replace backslash with slash, since xmind saves paths with slashes
UNIX_HYPERLINK_MEDIA_PATH = TEMPORARY_HYPERLINK_MEDIA_PATH.replace("\\", "/")
MEDIA_HYPERLINK_NODE_CONTENT = NodeContentDto(media=TEMPORARY_HYPERLINK_MEDIA_PATH)
MEDIA_ATTACHMENT_NODE_CONTENT: NodeContentDto = NodeContentDto(media='attachments/395ke7i9a6nkutu85fcpa66as2.mp4')
NEUROTRANSMITTERS_CLASS_NAME = 'neurotransmittersximage_629d18n2i73im903jkrjmr98fg_extension_png'
EMPTY_NODE_TAG_ID = "6b0ho6vvcs4pcacchhsgju7513"

EDGE_FOLLOWING_MULTIPLE_NOTES_FOREIGN_NOTE_PICKLE = \
    b'\x80\x04\x95\xff\x02\x00\x00\x00\x00\x00\x00\x8c\x16anki.importing.noteimp\x94\x8c\x0bForeignNote\x94\x93\x94' \
    b')\x81\x94}\x94(\x8c\x06fields\x94]\x94(\x8c\xc4biological psychology<li>investigates: information transfer and ' \
    b'processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: Serotonin, dopamine, ' \
    b'adrenaline, noradrenaline</li>\x94\x8c\x03are\x94\x8c\x0fbiogenic ' \
    b'amines\x94\x8c\x00\x94h\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\nh\n\x8c\t|{|{{{|\x7f{' \
    b'\x94e\x8c\x04tags\x94]\x94(\x8c  Example::test_file::test_sheet ' \
    b'\x94\x8c\x1a6iivm8tpoqj2c0euaabtput14l\x94e\x8c\x04deck\x94N\x8c\x05cards\x94}\x94K\x01h\x00\x8c\x0bForeignCard' \
    b'\x94\x93\x94)\x81\x94}\x94(\x8c\x03due\x94K\x00\x8c\x03ivl\x94K\x01\x8c\x06factor\x94M\xc4\t\x8c\x04reps\x94K' \
    b'\x00\x8c\x06lapses\x94K\x00ubs\x8c\tfieldsStr\x94\x8c\xf5biological psychology<li>investigates: information ' \
    b'transfer and processing</li><li>modulated by: enzymes</li><li>example: MAO</li><li>splits up: Serotonin, ' \
    b'dopamine, adrenaline, noradrenaline</li>\x1fare\x1fbiogenic ' \
    b'amines\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f\x1f|{|{{{|\x7f{\x94ub.'
EDGE_FOLLOWING_MULTIPLE_NODES_NOTE_ID = 12345
MULTIPLE_PARENTS_CONTENTS = [NodeContentDto(title=i) for i in ["Serotonin", "dopamine", "adrenaline", "noradrenaline"]]
MULTIPLE_PARENTS_CLASS_NAMES = [FieldTranslator().class_from_content(i) for i in MULTIPLE_PARENTS_CONTENTS]
MULTIPLE_PARENTS_NODE_IDS = ["56ru8hj8k8361ppfrftrbahgvv", "03eokjlomuockpeaqn2923nvvp", "3f5lmmd8mjhe3gkbnaih1m9q8j",
                             "73mo29opsuegqobtttlt2vbaqj"]
MULTIPLE_PARENTS_CHILD_CONTENT = NodeContentDto(title="biogenic amines")
MULTIPLE_PARENTS_CHILD_CLASS_NAME = FieldTranslator().class_from_content(MULTIPLE_PARENTS_CHILD_CONTENT)
MULTIPLE_PARENTS_CHILD_NODE_ID = "3oqcv5qlqhn28u1opce5i27709"
MULTIPLE_PARENTS_RELATION_CONTENT = NodeContentDto(title="are")
MULTIPLE_PARENTS_RELATION_CLASS_NAME = FieldTranslator().relation_class_from_content(MULTIPLE_PARENTS_RELATION_CONTENT)
