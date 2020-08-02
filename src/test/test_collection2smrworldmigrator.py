from main.collection2smrworldmigrator import Collection2SmrWorldMigrator


def test_collection2smr_world_migrator(collection_4_migration, empty_smr_world):
    cut = Collection2SmrWorldMigrator(col=collection_4_migration, smr_world=empty_smr_world)
