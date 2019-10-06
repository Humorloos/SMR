import re
from bs4 import BeautifulSoup

from XmindImport.xmind.xtopic import TopicElement


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
# the topic with the given topic id as a WorkbookElement
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
