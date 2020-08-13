import os
import smr.main as main
import smr.config as config
import smr.smrworld as smrworld
from smr.consts import X_MODEL_NAME, X_MODEL_VERSION, USER_PATH


def test_on_profile_loaded(mocker, empty_anki_collection_session):
    """Checks that the database that is created if there is no database yet is the same as the one that is loaded if it
    already exists"""
    # given
    models = {X_MODEL_NAME: {'vers': [X_MODEL_VERSION]}}
    mocker.patch("smr.config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("smr.main.mw")
    main.mw.col = empty_anki_collection_session
    mocker.patch("smr.main.SmrWorldMigrationDialog")
    # when
    main.on_profile_loaded()
    tables_database_present = [
        e[0] for e in main.mw.smr_world.graph.execute('SELECT name from sqlite_master where type = "table"').fetchall()]
    main.mw.smr_world.close()
    os.unlink(os.path.join(USER_PATH, smrworld.FILE_NAME))
    main.on_profile_loaded()
    tables_database_new = [
        e[0] for e in main.mw.smr_world.graph.execute('SELECT name from sqlite_master where type = "table"').fetchall()]
    main.mw.smr_world.close()
    # then
    assert tables_database_new == tables_database_present
