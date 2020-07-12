import os

import config
import main
import smrworld
from consts import X_MODEL_NAME, X_MODEL_VERSION, USER_PATH


def test_on_profile_loaded(mocker, empty_anki_collection):
    """Checks that the database that is created if there is no database yet is the same as the one that is loaded if it
    already exists"""
    models = {X_MODEL_NAME: {'vers': [X_MODEL_VERSION]}}
    mocker.patch("config.mw")
    config.mw.col.models.byName.side_effect = models.get
    mocker.patch("main.mw")
    main.mw.col = empty_anki_collection
    main.on_profile_loaded()
    tables_database_present = [
        e[0] for e in main.mw.smr_world.graph.execute('SELECT name from sqlite_master where type = "table"').fetchall()]
    main.mw.smr_world.close()
    os.unlink(os.path.join(USER_PATH, smrworld.FILE_NAME))
    main.on_profile_loaded()
    tables_database_new = [
        e[0] for e in main.mw.smr_world.graph.execute('SELECT name from sqlite_master where type = "table"').fetchall()]
    main.mw.smr_world.close()
    assert tables_database_new == tables_database_present
