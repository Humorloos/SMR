import re

from anki.models import ModelManager
from main.consts import X_MODEL_NAME

from anki.utils import ids2str


def deep_merge(remote, local, path=None):
    if path is None:
        path = []
    if path and path[-1] == 'questions' and not remote.keys() == local.keys():
        raise Exception('Error: Local and remote are not equal')
    for key in remote:
        if key in local:
            if isinstance(local[key], dict) and isinstance(remote[key],
                                                           dict):
                deep_merge(remote=remote[key], local=local[key],
                           path=path + [str(key)])
            elif local[key] == remote[key]:
                pass  # same leaf value
            else:
                raise Exception(
                    'Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            local[key] = remote[key]
    return local


# replace the anki sound html code with (sound) to avoid anki playing sounds
# when they are mentioned in the reference
def replaceSound(content: str):
    return re.sub("\[sound:.*\]", '(sound)', content)


# Receives a sortId of an anki note and returns the path that leads to the
# corresponding node in the xmind document
def get_edge_coordinates_from_parent_node(order_number, parent_node_ids):
    raise NotImplementedError


# receives a topic's id attribute, a BeautifulSoup object representing an
# xmind content xml file and a WorkbookDocument for the same map and returns
# the corresponding topic as a WorkbookElement
def getTopicById(tId, importer):
    tag = importer.soup.find('topic', {'id': tId})
    if not tag:
        return None
    # get tags that make up the path to the desired topic
    parents = list(tag.parents)
    topicPath = [tag]
    parentTopics = list(
        filter(lambda parent: parent.name == 'topic', parents))
    if len(parentTopics) > 1:
        topicPath.extend(parentTopics[:-1])
    # get the sheet that contains the topic
    sheetTag = list(reversed(parents))[2]
    sheetNr = len(list(sheetTag.previous_siblings))
    # noinspection PyProtectedMember
    sheet = importer.currentSheetImport['sheet']._owner_workbook.getSheets()[
        sheetNr]
    # starting at the root topic follow the path described by the tags to
    # get the desired topic
    topic = sheet.getRootTopic()
    for topicTag in reversed(topicPath):
        topicNr = len(list(topicTag.previous_siblings))
        topic = topic.getSubTopics()[topicNr]
    return topic


def getNotesFromSheet(sheetId, col):
    notes = list(col.db.execute(
        "select id, flds from notes where flds like '%\"sheetId\": \"" +
        sheetId + "\"%'"))
    if len(notes) > 0:
        return notes
    else:
        return None


def isSMRDeck(did, col):
    nidsInDeck = list(set(
        sum(col.db.execute("select nid from cards where did = " + str(did)),
            ())))
    midsInDeck = list(set(sum(col.db.execute(
        "select mid from notes where id in " + ids2str(nidsInDeck)), ())))
    return get_smr_model_id(col) in midsInDeck


def get_smr_model_id(model_manager: ModelManager) -> str:
    """
    gets anki's model id that was assigned to the smr model
    :param model_manager:
    :return:
    """
    return model_manager.id_for_name(X_MODEL_NAME)


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
