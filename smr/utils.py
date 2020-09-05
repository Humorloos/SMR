import re
from typing import Optional

from anki.models import ModelManager
from anki.utils import ids2str
from smr import consts as cts
from smr.consts import X_MODEL_NAME

MEDIA_REGEX = r'(\[sound:([^\[]*\.(' + '|'.join(cts.X_MEDIA_EXTENSIONS) + r'))])'


def get_smr_model_id(model_manager: ModelManager) -> Optional[int]:
    """
    gets anki's model id that was assigned to the smr model
    :param model_manager: model manager from the anki collection containing the model
    """
    return model_manager.id_for_name(X_MODEL_NAME)


def replace_embedded_media(content: str) -> str:
    """
    replaces embedded anki media with (media) to avoid anki playing sounds or videos when they are mentioned in the
    reference
    :param content: the content in which to replace the embeddings
    :return: the content with replaced media embeddings
    """
    return re.sub(MEDIA_REGEX, '(media)', re.sub(r'(<br>)' + MEDIA_REGEX, r' \2', content))


def getDueAnswersToNote(nId, dueAnswers, col):
    cardTpls = list(col.db.execute(
        """select id, ord from cards where nid = ? and id in """ + ids2str(
            dueAnswers), nId))
    cards = []
    for cardTpl in cardTpls:
        cards.append(dict(cId=cardTpl[0], ord=cardTpl[1]))
    return cards


def file_dict(identifier, doc):
    return {'identifier': identifier, 'doc': doc}
