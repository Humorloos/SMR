import os
import re

import bs4
import pandas as pd
import pytest

import main.smrworld as smrworld
import main.xmanager as xmanager
import main.xmindimport as xmindimport
import main.xontology as xontology
import test.constants as cts
from anki import Collection
from main import config
from main.config import get_or_create_smr_world

TEST_WORLD_NAME = "testworld.sqlite3"


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
        os.unlink(os.path.join(cts.SMR_WORLD_PATH, TEST_WORLD_NAME))
    except FileNotFoundError:
        pass
    standard_world_file_name = smrworld.FILE_NAME
    standard_user_path = smrworld.USER_PATH
    standard_user_path_config = config.USER_PATH
    smrworld.FILE_NAME = TEST_WORLD_NAME
    smrworld.USER_PATH = cts.SMR_WORLD_PATH
    config.USER_PATH = cts.SMR_WORLD_PATH
    yield
    smrworld.FILE_NAME = standard_world_file_name
    smrworld.USER_PATH = standard_user_path
    config.USER_PATH = standard_user_path_config
    assert True


@pytest.fixture
def empty_smr_world(patch_empty_smr_world) -> smrworld.SmrWorld:
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()


@pytest.fixture(scope="session")
def _smr_world_for_tests_session(empty_anki_collection_session):
    smrworld.FILE_NAME = "smr_world_for_tests.sqlite3"
    smrworld.USER_PATH = cts.SMR_WORLD_PATH
    smr_world_path = os.path.join(cts.SMR_WORLD_PATH, smrworld.FILE_NAME)
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


@pytest.fixture()
def smr_world_for_tests(_smr_world_for_tests_session):
    smr_world = _smr_world_for_tests_session
    yield smr_world
    smr_world.graph.db.rollback()


@pytest.fixture
def x_manager():
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
    x_ontology._smr_world.close()


@pytest.fixture
def xmind_importer(mocker, empty_anki_collection_session) -> xmindimport.XmindImporter:
    """
    XmindImporter instance for file example map.xmind
    """
    mocker.patch("aqt.mw")
    yield xmindimport.XmindImporter(col=empty_anki_collection_session, file=cts.EXAMPLE_MAP_PATH)
