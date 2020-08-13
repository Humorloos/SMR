import os
from typing import Dict, List

from aqt import mw
from smr.consts import X_MODEL_NAME, X_MODEL_VERSION, SMR_CONFIG, USER_PATH
from smr.smrworld import SmrWorld, FILE_NAME
from smr.template import update_x_model, add_x_model
from xversion.xversion import LooseVersion


def create_or_update_model() -> None:
    """
    Creates the SMR model if it is not yet created and returns it.
    :return: the SMR model
    """
    model: Dict[str, List[str]] = mw.col.models.byName(X_MODEL_NAME)
    if not model:
        # create model
        add_x_model(mw.col)
    elif len(model['vers']) == 0 or LooseVersion(model['vers'][-1]) < LooseVersion(X_MODEL_VERSION):
        update_x_model(mw.col)


def update_smr_version():
    """
    Updates the Addon Version
    """
    mw.col.set_config('smr', SMR_CONFIG)


def get_or_create_smr_world() -> SmrWorld:
    """
    Sets up the smr world when the addon is first installed or updated to the first version that implements it.
    :return: the smr world
    """
    if not os.path.isfile(os.path.join(USER_PATH, FILE_NAME)):
        smr_world: SmrWorld = SmrWorld()
        smr_world.set_up()
    else:
        smr_world: SmrWorld = SmrWorld()
    return smr_world
