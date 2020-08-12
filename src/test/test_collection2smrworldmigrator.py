import pytest

import test.constants as cts
from main.collection2smrworldmigrator import Collection2SmrWorldMigrator
from main.xmanager import XManager


@pytest.fixture
def collection_2_smr_world_migrator(collection_4_migration, patch_aqt_mw_empty_smr_world):
    patch_aqt_mw_empty_smr_world.col = collection_4_migration
    return Collection2SmrWorldMigrator()


def test_migrate_deck_2_smr_world(collection_2_smr_world_migrator):
    # given
    cut = collection_2_smr_world_migrator
    # when
    cut._migrate_deck_2_smr_world(smr_deck_id=1579442668731)
    # then
    assert len(cut.smr_world.graph.execute("select * from main.xmind_files").fetchall()) == 2
    assert len(cut.smr_world.graph.execute("select * from main.xmind_sheets").fetchall()) == 3
    assert len(cut.smr_world.graph.execute("select * from main.xmind_media_to_anki_files").fetchall()) == 4
    assert len(cut.smr_world.graph.execute("select * from main.smr_notes").fetchall()) == 30
    assert len(cut.smr_world.graph.execute("select * from main.xmind_edges").fetchall()) == cts.EXAMPLE_MAP_N_EDGES
    assert len(cut.smr_world.graph.execute("select * from main.smr_triples").fetchall()) == 46
    assert len(cut.smr_world.graph.execute("select * from main.xmind_nodes").fetchall()) == 46


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


@pytest.mark.skip(reason="This test takes far too for running it each time")
def test_migrate_collection_2_smr_world2(real_collection_4_migration, patch_aqt_mw_empty_smr_world):
    # given
    patch_aqt_mw_empty_smr_world.col = real_collection_4_migration
    cut = Collection2SmrWorldMigrator()
    # when
    cut.migrate_collection_2_smr_world()
    # then
    pass


def test_migrate_collection_2_smr_world(collection_4_migration, patch_aqt_mw_empty_smr_world):
    # given
    patch_aqt_mw_empty_smr_world.col = collection_4_migration
    cut = Collection2SmrWorldMigrator()
    # when
    cut.migrate_collection_2_smr_world()
    # then
    # make sure the right tags are assigned to the updated notes
    assert len(cut.collection.db.list(
        "select id from notes where tags = ' Example::example_map::biological_psychology '")) > 0
