import re
import urllib.parse
import os
import zipfile
import tempfile
import shutil
from bs4 import BeautifulSoup

from anki.utils import ids2str

from .consts import X_MODEL_NAME


# checks whether a node contains any text, images or link
def isEmptyNode(tag):
    if getNodeTitle(tag):
        return False
    if getNodeImg(tag):
        return False
    if getNodeHyperlink(tag):
        return False
    return True


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


def getAnswerDict(nodeTag):
    # Check whether subtopic is not empty
    isAnswer = True
    if isEmptyNode(nodeTag):
        isAnswer = False
    # Check whether subtopic contains a crosslink
    crosslink = getNodeCrosslink(nodeTag)
    return dict(nodeTag=nodeTag, isAnswer=isAnswer, aId=str(0),
                crosslink=crosslink)


def getNotesFromSheet(sheetId, col):
    notes = list(col.db.execute(
        "select id, flds from notes where flds like '%\"sheetId\": \"" +
        sheetId + "\"%'"))
    if len(notes) > 0:
        return notes
    else:
        return None


def isSMRDeck(did, col):
    nidsInDeck = set(nid for nid_list in col.db.execute(
        "select nid from cards where did = " + str(did)) for nid in nid_list)
    midsInDeck = set(mid for mid_list in col.db.execute(
        "select mid from notes where id in " + ids2str(nidsInDeck)) for mid in mid_list)
    return xModelId(col) in midsInDeck


def xModelId(col):
    return col.models.id_for_name(X_MODEL_NAME)


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


def getNodeContent(tagList, tag):
    content = ''
    media = dict(image=None, media=None)
    href = getNodeHyperlink(tag)
    title = getNodeTitle(tag)

    if title:
        content += '<span class = "title">' + title

    # If the node contains a link to another node, add the text of that
    # node. Use Beautifulsoup because minidom can't find nodes by attributes
    if href and href.startswith('xmind:#'):
        crosslinkTag = getTagById(tagList=tagList, tagId=href[7:])
        crosslinkTitle = getNodeTitle(crosslinkTag)
        if content:
            content += ' '
            content += crosslinkTitle
        else:
            content += '<span class = "title">' + crosslinkTitle
    if content:
        content += '</span>'

    # if necessary add image
    attachment = getNodeImg(tag=tag)
    if attachment:
        if content != '':
            content += '<br>'
        fileName = re.search('/.*', attachment).group()[1:]
        content += '<img src="%s">' % fileName
        media['image'] = attachment[4:]

    # if necessary add sound
    if href and href.endswith(('.mp3', '.wav', 'mp4')):
        if content:
            content += '<br>'
        if href.startswith('file'):
            mediaPath = urllib.parse.unquote(href[5:])
            media['media'] = mediaPath
        else:
            mediaPath = href[4:]
            media['media'] = mediaPath
        content += '[sound:%s]' % os.path.basename(mediaPath)
    return content, media


def getTagById(tagList, tagId):
    try:
        return tuple(filter(lambda t: t['id'] == tagId, tagList))[0]
    except IndexError:
        return None


def getNodeTitle(tag):
    try:
        return tag.find('title', recursive=False).text
    except AttributeError:
        return ''


def setNodeTitle(tag, title):
    tag.find('title', recursive=False).string = title


def getNodeImg(tag):
    try:
        return tag.find('xhtml:img', recursive=False)['xhtml:src']
    except (TypeError, AttributeError):
        return None


def getNodeHyperlink(tag):
    try:
        return tag['xlink:href']
    except (KeyError, TypeError):
        return None


def getNodeCrosslink(tag):
    href = getNodeHyperlink(tag)
    if href and href.startswith('xmind:#'):
        return href[7:]
    else:
        return None


def getChildnodes(tag):
    try:
        return tag.find('children', recursive=False).find(
            'topics', recursive=False)('topic', recursive=False)
    except AttributeError:
        return []


def titleFromContent(content):
    try:
        return BeautifulSoup(content, features="lxml").select('.title')[
            0].text
    except IndexError:
        return re.sub("(<br>)?(\[sound:.*\]|<img src=.*>)", "", content)


def imgFromContent(content):
    try:
        return re.search('<img src=\"(.*\.(jpg|png))\">', content).group(1)
    except AttributeError:
        return None

