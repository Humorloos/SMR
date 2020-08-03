import os
from collections import OrderedDict

# SMR Version
SMR_CONFIG = {
    'version': '0.1.0'
}

# SMR Template information
X_MODEL_VERSION = '0.2.0'
X_MODEL_NAME = 'Stepwise Map Retrieval'
X_MAX_ANSWERS = 20
X_CARD_NAMES = list(map(lambda aswid: 'Answer ' + str(aswid),
                        list(range(1, X_MAX_ANSWERS + 1))))
X_MEDIA_EXTENSIONS = ('mp3', 'wav', 'mp4')
X_IMAGE_EXTENSIONS = ('jpeg', 'jpg', 'png')

# Fields, use orderedDict to be able to access flds field in notes objects by postition of dictionary key
SMR_NOTE_FIELD_NAMES: OrderedDict = OrderedDict((('rf', 'Reference'), ('qt', 'Question')))
for i in range(1, X_MAX_ANSWERS + 1):
    SMR_NOTE_FIELD_NAMES['a' + str(i)] = 'Answer ' + str(i)
SMR_NOTE_FIELD_NAMES.update({
    'id': 'ID',
})
X_SORT_FIELD = 'id'


# IDs of Fields
SMR_FIELD_IDENTIFIERS = ['rf', 'qt'] + list(map(lambda aswid: 'a' + str(aswid), list(range(1, X_MAX_ANSWERS + 1)))) + [
    'id']

# Path constants:
ADDON_PATH = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]

USER_PATH = os.path.join(ADDON_PATH, 'user_files')

ICONS_PATH = os.path.join(ADDON_PATH, "icons")
