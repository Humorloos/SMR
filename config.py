import os

from consts import X_MODEL_NAME, X_MODEL_VERSION, SMR_CONFIG, USER_PATH
from owlready2.namespace import World
from template import update_x_model, add_x_model
from ximports.xversion import LooseVersion

from aqt import mw


def get_or_create_model():
    """
    Creates the SMR model if it is not yet created and returns it.
    :return: the SMR model
    """
    model = mw.col.models.byName(X_MODEL_NAME)
    if not model:
        # create model
        model = add_x_model(mw.col)
    if len(model['vers']) == 0 or LooseVersion(model['vers'][-1]) < LooseVersion(X_MODEL_VERSION):
        update_x_model(mw.col)
    return model


def look_up_version():
    if 'smr' not in mw.col.conf:
        set_up_ontology()
    if 'smr' not in mw.col.conf or \
            LooseVersion(mw.col.conf['smr']['version']) < \
            LooseVersion(SMR_CONFIG['version']):
        mw.col.conf['smr'] = SMR_CONFIG


def set_up_ontology():
    world = World(filename=os.path.join(USER_PATH, 'onto.sqlite3'))
    world.save()
    pass
