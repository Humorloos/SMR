from .ximports.xversion import LooseVersion

from aqt import mw

from .template import *


def get_or_create_model():
    model = mw.col.models.byName(X_MODEL_NAME)
    if not model:
        # create model
        model = add_x_model(mw.col)
    if len(model['vers']) == 0 or \
            LooseVersion(model['vers'][-1]) < LooseVersion(X_MODEL_VERSION):
        update_x_model(mw.col)
    return model
