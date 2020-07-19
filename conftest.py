import os
from imp import reload

import pandas as pd
import csv
import bs4
import pytest
import smrworld
import xmanager
import XmindImport.tests.constants as cts
import xontology
from config import get_or_create_smr_world
from pandas.errors import EmptyDataError

from anki import Collection
import re

TEST_WORLD_NAME = "testworld.sqlite3"


@pytest.fixture(scope="session")
def empty_anki_collection() -> Collection:
    collection = cts.EMPTY_COLLECTION
    yield collection
    collection.close(save=False)


@pytest.fixture()
def patch_empty_smr_world() -> None:
    standard_world = smrworld.FILE_NAME
    smrworld.FILE_NAME = TEST_WORLD_NAME
    yield
    smrworld.FILE_NAME = standard_world
    os.unlink(os.path.join(smrworld.USER_PATH, TEST_WORLD_NAME))


@pytest.fixture
def empty_smr_world(patch_empty_smr_world) -> smrworld.SmrWorld:
    # modify smrworld so that the world that is loaded is not the actual world in user_files but an empty World
    smr_world = smrworld.SmrWorld()
    yield smr_world
    smr_world.close()


@pytest.fixture(scope="session")
def _smr_world_for_tests_session(empty_anki_collection):
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
                          'main_ontology_lives_in_deck.csv', 'main_xmind_files.csv', 'main_xmind_sheets.csv',
                          'main_xmind_nodes.csv', 'main_xmind_edges.csv', 'main_smr_triples.csv',
                          'main_smr_notes.csv']
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
    mocker.patch('xontology.mw')
    xontology.mw.smr_world = get_or_create_smr_world()
    mocker.spy(xontology.XOntology, "_set_up_classes")
    x_ontology = xontology.XOntology("99999")
    yield x_ontology
    xontology.mw.smr_world.close()
