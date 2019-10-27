import re
from bs4 import BeautifulSoup

from anki.collection import _Collection
from anki.utils import ids2str, splitFields

from .xmind.xtopic import TopicElement
from .consts import X_MODEL_NAME, X_FLDS


# checks whether a node contains any text, images or link
def isEmptyNode(node: TopicElement):
    if node.getTitle():
        return False
    if node.getFirstChildNodeByTagName('xhtml:img'):
        return False
    if node.getAttribute('xlink:href'):
        return False
    return True


# receives a dictionary with an id for sorting the cards and an id for finding the card's position
def updateId(previousId, idToAppend):
    return previousId + chr(idToAppend + 122)


# replace the anki sound html code with (sound) to avoid anki playing sounds
# when they are mentioned in the reference
def replaceSound(content: str):
    return re.sub("\[sound:.*\]", '(sound)', content)


# Receives a sortId of an anki note and returns the path that leads to the
# corresponding node in the xmind document
def getCoordsFromId(sortId):
    indices = list(map(lambda index: str(ord(index) - 122), sortId))
    coords = indices[0]
    for index in indices[1:]:
        coords += '.' + index
    return coords


# receives a topic's id attribute, a BeautifulSoup object representing an
# xmind content xml file and a WorkbookDocument for the same map and returns
# the corresponding topic as a WorkbookElement
def getTopicById(tId, importer):
    # TODO: implement warning if topic not found
    tag = importer.soup.find('topic', {'id': tId})
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


# receives a string to search for in meta fields of SMR Notes and returns the
# first note to contain the delivered String
def getNoteFromMeta(query, col: _Collection):
    SMRNids = getSMRNids(col)
    nIdString = ids2str(SMRNids)
    for nid, flds in col.db.execute(
            "select id, flds from notes where id in " + nIdString):
        splitFlds = splitFields(flds)
        if query in splitFlds[list(X_FLDS.keys()).index('mt')]:
            return nid
    return None


# Receives the id of a Question node from the concept map and returns the
# corresponding Note from the collection. Returns None if no note was found
def getNoteFromQuestion(qId, col: _Collection):
    query = "\"questionId\": \"%s\"" % qId
    return getNoteFromMeta(query=query, col=col)


# receives a collection and returns a list of nIds for all notes of type SMR
def getSMRNids(col: _Collection):
    return col.findNotes('"note:%s"' % X_MODEL_NAME)


# Receives the id of an Answer node from the concept map and returns the
# corresponding Note from the collection. Returns None if no note was found
def getNoteFromAnswer(aId, col: _Collection):
    query = "\"answerId\": \"%s\"" % aId
    return getNoteFromMeta(query=query, col=col)


# receives a minidom Element representing an xmind Topic (retrieved with
# topic._node) and returns its parent Element as a minidom Element
def getParentTopicElement(element):
    return element.parentNode.parentNode.parentNode


# Receives an xmind TopicElement and returns the id attribute of its parent
# topic
def getParentTopicId(topic: TopicElement):
    parentTopic = getParentTopicElement(topic._node)
    return parentTopic.getAttribute('id')


def getParentTopic(topic: TopicElement, importer):
    parentId = getParentTopicId(topic)
    return getTopicById(tId=parentId, importer=importer)


def getAnswerDict(subTopic: TopicElement):
    # Check whether subtopic is not empty
    isAnswer = True
    if isEmptyNode(subTopic):
        isAnswer = False
    # Check whether subtopic contains a crosslink
    crosslink = getCrosslink(subTopic)
    return dict(subTopic=subTopic, isAnswer=isAnswer, aId=str(0),
                crosslink=crosslink)


def isConcept(topic):
    element = topic._node
    nParentTopics = 0
    while type(element).__name__ == 'Element':
        nParentTopics += 1
        element = getParentTopicElement(element)
    if nParentTopics % 2 == 0:
        return False
    else:
        return True


def getCrosslink(topic):
    href = topic.getHyperlink()
    if href and href.startswith('xmind:#'):
        return href[7:]
    else:
        return None


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
    return xModelId(col) in midsInDeck


def xModelId(col):
    return int(list(filter(lambda v: v['name'] == X_MODEL_NAME,
                       list(col.models.models.values())))[0]['id'])
