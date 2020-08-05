import os
import pickle
import aqt
import pytest
import test.constants as cts
from main.collection2smrworldmigrator import Collection2SmrWorldMigrator
import main.collection2smrworldmigrator
from main.xmanager import XManager


@pytest.fixture
def collection_2_smr_world_migrator(collection_4_migration, set_up_empty_smr_world):
    yield Collection2SmrWorldMigrator(col=collection_4_migration, smr_world=set_up_empty_smr_world)


def test_migrate_deck_2_smr_world(collection_2_smr_world_migrator, mocker, set_up_empty_smr_world):
    # given
    cut = collection_2_smr_world_migrator
    mocker.patch('aqt.mw')
    aqt.mw.smr_world = set_up_empty_smr_world
    aqt.mw.return_value = aqt.mw
    # when
    cut._migrate_deck_2_smr_world(smr_deck_id=1579442668731)
    # then
    assert len(cut._smr_world.graph.execute("select * from main.xmind_files").fetchall()) == 2
    assert len(cut._smr_world.graph.execute("select * from main.xmind_sheets").fetchall()) == 3
    assert len(cut._smr_world.graph.execute("select * from main.xmind_media_to_anki_files").fetchall()) == 4
    assert len(cut._smr_world.graph.execute("select * from main.smr_notes").fetchall()) == cts.EXAMPLE_MAP_N_EDGES
    assert len(cut._smr_world.graph.execute("select * from main.xmind_edges").fetchall()) == cts.EXAMPLE_MAP_N_EDGES
    assert len(cut._smr_world.graph.execute("select * from main.smr_triples").fetchall()) == 37
    assert len(cut._smr_world.graph.execute("select * from main.xmind_nodes").fetchall()) == 40


def test_migrate_deck_2_smr_world_file_not_found(collection_2_smr_world_migrator, mocker):
    # given
    cut = collection_2_smr_world_migrator
    mocker.patch.object(cut, "_get_deck_data", return_value={cts.ABSENT_XMIND_FILE_PATH: []})
    # then
    with pytest.raises(FileNotFoundError) as exception_info:
        # when
        cut._migrate_deck_2_smr_world(smr_deck_id=1579442668731)
    # then
    assert exception_info.value.args[0] == XManager.FILE_NOT_FOUND_MESSAGE.format(cts.ABSENT_XMIND_FILE_PATH)