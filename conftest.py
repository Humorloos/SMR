import os
import re
import shutil

import bs4
import pandas as pd
import pytest

import aqt
import smr.config as config
import smr.smrworld as smrworld
import smr.xmanager as xmanager
import smr.xmindimport as xmindimport
import smr.xontology as xontology
import tests.constants as cts
from anki import Collection
from smr.config import get_or_create_smr_world


@pytest.fixture(scope="session")
def empty_anki_collection_session() -> Collection:
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_PATH_SESSION))
    except FileNotFoundError:
        pass
    collection = Collection(cts.EMPTY_COLLECTION_PATH_SESSION)
    yield collection
    collection.close()


@pytest.fixture(scope="function")
def empty_anki_collection_function() -> Collection:
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_PATH_FUNCTION))
    except FileNotFoundError:
        pass
    collection = Collection(cts.EMPTY_COLLECTION_PATH_FUNCTION)
    yield collection
    collection.close()


@pytest.fixture(scope="function")
def patch_empty_smr_world() -> None:
    try:
        os.unlink(os.path.join(cts.SMR_WORLD_PATH, cts.EMPTY_SMR_WORLD_NAME))
    except FileNotFoundError:
        pass
    standard_world_path = smrworld.SMR_WORLD_PATH
    standard_user_path_config = config.USER_PATH
    smrworld.SMR_WORLD_PATH = os.path.join(cts.SMR_WORLD_PATH, cts.EMPTY_SMR_WORLD_NAME)
    config.USER_PATH = cts.SMR_WORLD_PATH
    yield
    smrworld.SMR_WORLD_PATH = standard_world_path
    config.USER_PATH = standard_user_path_config


@pytest.fixture
def empty_smr_world(patch_empty_smr_world) -> smrworld.SmrWorld:
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.save()
    smr_world.close()


@pytest.fixture
def set_up_empty_smr_world(empty_smr_world):
    smr_world = empty_smr_world
    smr_world.set_up()
    yield smr_world


@pytest.fixture(scope="session")
def _smr_world_for_tests_session(empty_anki_collection_session):
    smr_world_path = os.path.join(cts.SMR_WORLD_PATH, "smr_world_4_tests.sqlite3")
    smrworld.SMR_WORLD_PATH = smr_world_path
    try:
        os.unlink(smr_world_path)
    except FileNotFoundError:
        pass
    smr_world = smrworld.SmrWorld()
    smr_world.set_up()
    relevant_csv_files = ['main_datas.csv', 'main_objs.csv', 'main_ontologies.csv', 'main_ontology_alias.csv',
                          'main_prop_fts.csv', 'main_resources.csv', 'main_store.csv',
                          'main_xmind_media_to_anki_files.csv', 'main_ontology_lives_in_deck.csv',
                          'main_xmind_files.csv', 'main_xmind_sheets.csv', 'main_xmind_nodes.csv',
                          'main_xmind_edges.csv', 'main_smr_triples.csv', 'main_smr_notes.csv']
    for csv_filename in relevant_csv_files:
        table: str = re.sub("main_|.csv", '', csv_filename)
        csv_file_path = os.path.join(cts.SMR_WORLD_CSV_PATH, csv_filename)
        # noinspection SqlWithoutWhere
        smr_world.graph.execute("DELETE FROM {}".format(table))
        df = pd.read_csv(csv_file_path)
        df.to_sql(name=table, con=smr_world.graph.db, if_exists='append', index=False)
    yield smr_world
    smr_world.close()


@pytest.fixture(scope="function")
def smr_world_with_example_map():
    test_world_path = os.path.join(cts.SMR_WORLD_PATH, "smr_world_with_example_map.sqlite3")
    try:
        os.unlink(test_world_path)
    except FileNotFoundError:
        pass
    shutil.copy(src=cts.SMR_WORLD_WITH_EXAMPLE_MAP_PATH,
                dst=test_world_path)
    standard_world_path = smrworld.SMR_WORLD_PATH
    standard_user_path_config = config.USER_PATH
    smrworld.SMR_WORLD_PATH = test_world_path
    config.USER_PATH = cts.SMR_WORLD_PATH
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()
    smrworld.SMR_WORLD_PATH = standard_world_path
    config.USER_PATH = standard_user_path_config


@pytest.fixture(scope="function")
def collection_4_migration():
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_PATH_FUNCTION))
    except FileNotFoundError:
        pass
    shutil.copy(src=os.path.join(cts.TEST_COLLECTIONS_PATH, 'collection_version_0.0.1', 'collection.anki2'),
                dst=cts.EMPTY_COLLECTION_PATH_FUNCTION)
    col = Collection(cts.EMPTY_COLLECTION_PATH_FUNCTION)
    yield col
    col.close()


@pytest.fixture(scope="function")
def real_collection_4_migration():
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_PATH_FUNCTION))
    except FileNotFoundError:
        pass
    shutil.copy(src=os.path.join(cts.TEST_COLLECTIONS_PATH, 'real_collection_version_0.0.1', 'collection.anki2'),
                dst=cts.EMPTY_COLLECTION_PATH_FUNCTION)
    col = Collection(cts.EMPTY_COLLECTION_PATH_FUNCTION)
    yield col
    col.close()


@pytest.fixture()
def smr_world_4_tests(_smr_world_for_tests_session):
    smr_world = _smr_world_for_tests_session
    yield smr_world
    smr_world.graph.db.rollback()


@pytest.fixture(scope="function")
def x_manager() -> xmanager.XManager:
    yield xmanager.XManager(cts.EXAMPLE_MAP_PATH)


@pytest.fixture
def tag_for_tests():
    with open(os.path.join(cts.SUPPORT_PATH, 'xmindImporter', 'content.xml'), 'r') as file:
        tag = bs4.BeautifulSoup(file.read(), features='html.parser').topic
        file.close()
    yield tag


@pytest.fixture()
def x_ontology(mocker, patch_empty_smr_world) -> xontology.XOntology:
    mocker.spy(xontology.XOntology, "_set_up_classes")
    x_ontology = xontology.XOntology("99999", get_or_create_smr_world())
    yield x_ontology
    # noinspection PyProtectedMember
    x_ontology.smr_world.close()


@pytest.fixture
def xmind_importer(mocker, empty_anki_collection_session) -> xmindimport.XmindImporter:
    """
    XmindImporter instance for file example map.xmind
    """
    mocker.patch("aqt.mw")
    yield xmindimport.XmindImporter(col=empty_anki_collection_session, file=cts.EXAMPLE_MAP_PATH)


@pytest.fixture
def patch_aqt_mw_empty_smr_world(mocker, set_up_empty_smr_world):
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = set_up_empty_smr_world
    aqt.mw.return_value = aqt.mw
    yield aqt.mw


@pytest.fixture
def collection_with_example_map():
    try:
        os.unlink(os.path.join(cts.EMPTY_COLLECTION_PATH_FUNCTION))
    except FileNotFoundError:
        pass
    shutil.copy(src=os.path.join(cts.TEST_COLLECTIONS_PATH, 'collection_with_example_map', 'collection.anki2'),
                dst=cts.EMPTY_COLLECTION_PATH_FUNCTION)
    col = Collection(cts.EMPTY_COLLECTION_PATH_FUNCTION)
    yield col
    col.close()


@pytest.fixture
def changed_collection_with_example_map():
    try:
        os.unlink(os.path.join(cts.CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH))
    except FileNotFoundError:
        pass
    shutil.copy(src=os.path.join(cts.TEST_COLLECTIONS_PATH, 'collection_with_example_map_changes', 'collection.anki2'),
                dst=cts.CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    try:
        shutil.rmtree(cts.CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    except FileNotFoundError:
        pass
    shutil.copytree(src=os.path.join(cts.TEST_COLLECTIONS_PATH, 'collection_with_example_map_changes',
                                     'collection.media'), dst=cts.CHANGED_COLLECTION_WITH_EXAMPLE_MAP_MEDIA)
    col = Collection(cts.CHANGED_COLLECTION_WITH_EXAMPLE_MAP_PATH)
    yield col
    col.close()


@pytest.fixture
def patch_aqt_mw_smr_world_and_col_with_example_map(mocker, smr_world_with_example_map, collection_with_example_map):
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_with_example_map
    aqt.mw.col = collection_with_example_map
    aqt.mw.return_value = aqt.mw
    yield aqt.mw


@pytest.fixture
def patch_aqt_mw_smr_world_and_changed_col_with_example_map(mocker, smr_world_with_example_map,
                                                            changed_collection_with_example_map):
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = smr_world_with_example_map
    aqt.mw.col = changed_collection_with_example_map
    aqt.mw.return_value = aqt.mw
    yield aqt.mw


@pytest.fixture
def patch_aqt_mw_empty_smr_world_and_collection_4_migration(patch_aqt_mw_empty_smr_world, collection_4_migration):
    aqt.mw.col = collection_4_migration
    yield
