import re
from bs4 import BeautifulSoup

from anki.collection import _Collection
from anki.utils import ids2str, splitFields

from XmindImport.xmind.xtopic import TopicElement
from XmindImport.consts import X_MODEL_NAME, X_FLDS


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


# receives an answer node and returns all questions following this answer
# including questions following multiple topics as dictionaries of a question
# node and its corresponding reference
def findQuestionDicts(answer: TopicElement, ref=''):
    followRels = answer.getSubTopics()
    questionDicts = []
    for followRel in followRels:
        if isEmptyNode(followRel):
            for nextA in followRel.getSubTopics():
                nextQPairs = findQuestionDicts(
                    answer=nextA, ref=ref + '<li>' + nextA.getTitle())
                questionDicts.extend(nextQPairs)
        else:
            questionDicts.append(dict(question=followRel, ref=ref))
    return questionDicts


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
def getTopicById(tId: str, soup: BeautifulSoup, doc):
    tag = soup.find('topic', {'id': tId})
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
    sheet = doc.getSheets()[sheetNr]
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


# receives an xmind TopicElement and returns its parent Element as a minidom
# Element
def getParentTopic(topic: TopicElement):
    return topic.getParentNode().parentNode.parentNode


# Receives an xmind TopicElement and returns the id attribute of its parent
# topic
def getParentTopicId(topic: TopicElement):
    parentTopic = getParentTopic(topic)
    return parentTopic.getAttribute('id')


def getSiblingTopics(topic: TopicElement):
    print('')
    # TODO: Implement this


def getAnswerDict(subTopic: TopicElement):
    # Check whether subtopic is not empty
    isAnswer = True
    if isEmptyNode(subTopic):
        isAnswer = False
    # Check whether subtopic contains a crosslink
    crosslink = None
    href = subTopic.getHyperlink()
    if href and href.startswith('xmind:#'):
        crosslink = href
    return dict(subTopic=subTopic, isAnswer=isAnswer, aId=str(0),
                crosslink=crosslink)
