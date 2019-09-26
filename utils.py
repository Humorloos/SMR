import re

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
def updateIds(previousIds: dict, idToAppend):
    newIds = dict.copy(previousIds)
    newIds['sortId'] += chr(idToAppend + 122)
    if newIds['refId'] != '':
        newIds['refId'] += '.'
    newIds['refId'] += str(idToAppend)
    return newIds


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


def replaceSound(content: str):
    return re.sub("\[sound:.*\]", '(sound)', content)
