import re
import urllib.parse
import os
import zipfile
import tempfile
import shutil
from bs4 import BeautifulSoup

from anki.utils import ids2str

from .consts import X_MODEL_NAME


def classify(className):
    return className.replace(" ", "_")


def unclassify(className):
    return className.replace("_", " ")


def isQuestionNode(tag, level=0):
    # If the Tag is the root topic, return true if the length of the path is odd
    if tag.parent.name == 'sheet':
        return level % 2 == 1
    # Else add one to the path length and test again
    return isQuestionNode(tag.parent.parent.parent, level + 1)


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
    if sortId == '':
        return '0'
    indices = list(map(lambda index: str(ord(index) - 122), sortId))
    coords = indices[0]
    for index in indices[1:]:
        coords += '.' + index
    return coords


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
    return xModelId(col) in midsInDeck


def xModelId(col):
    return int(list(filter(lambda v: v['name'] == X_MODEL_NAME,
                           list(col.models.models.values())))[0]['id'])


def getNotesFromQIds(qIds, col):
    return sum(map(lambda qId: col.db.list(
        "select id from notes where flds like '%\"questionId\": \"" +
        qId + "\"%'"), qIds), [])


def getDueAnswersToNote(nId, dueAnswers, col):
    cardTpls = list(col.db.execute(
        """select id, ord from cards where nid = ? and id in """ + ids2str(
            dueAnswers), nId))
    cards = []
    for cardTpl in cardTpls:
        cards.append(dict(cId=cardTpl[0], ord=cardTpl[1]))
    return cards


def setNodeTitle(tag, title):
    tag.find('title', recursive=False).string = title


def titleFromContent(content):
    try:
        return BeautifulSoup(content, features="html.parser").select('.title')[
            0].text
    except IndexError:
        return re.sub("(<br>)?(\[sound:.*\]|<img src=.*>)", "", content)


def imgFromContent(content):
    try:
        return re.search('<img src=\"(.*\.(jpg|png))\">', content).group(1)
    except AttributeError:
        return None


def file_dict(identifier, doc):
    return {'identifier': identifier, 'doc': doc}