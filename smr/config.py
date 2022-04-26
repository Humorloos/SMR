from aqt import mw

from ..ximports.xversion import LooseVersion
from .template import *


def get_or_create_model():
    model = mw.col.models.by_name(X_MODEL_NAME)
    if not model:
        # create model
        model = add_x_model(mw.col)
    if 'version' not in model.keys() or \
            len(model['version']) == 0 or \
            LooseVersion(model['version'][-1]) < LooseVersion(X_MODEL_VERSION):
        update_x_model(mw.col)
    return model
