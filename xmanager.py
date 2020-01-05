# class for reading and writing xmind files

import os
import urllib.parse
import re
import zipfile

from bs4 import BeautifulSoup

class XManager:
    def __init__(self, file):
        xZip = zipfile.ZipFile(file, 'r')
        self.file = file
        self.soup = BeautifulSoup(xZip.read('content.xml'),
                                  features='html.parser')
        self.tagList = self.soup('topic')
        self.sheets = dict()
        for sheet in self.soup('sheet'):
            sheetTitle = sheet('title', recursive=False)[0].text
            self.sheets[sheetTitle] = sheet

    def getNodeContent(self, tag):
        """
        :param tag: the tag to get the content for
        :return: dictionary containing the content of the node as a string,
            an optional url to an image and a media file
        """
        content = ''
        media = dict(image=None, media=None)
        href = self.getNodeHyperlink(tag)
        title = self.getNodeTitle(tag)

        if title:
            content += title

        # If the node contains a link to another node, add the text of that
        # node. Use Beautifulsoup because minidom can't find nodes by attributes
        if href and href.startswith('xmind:#'):
            crosslinkTag = self.getTagById(tagId=href[7:])
            crosslinkTitle = self.getNodeTitle(crosslinkTag)
            if content:
                content += ' '
                content += crosslinkTitle
            else:
                content = crosslinkTitle

        # if necessary add image
        attachment = self.getNodeImg(tag=tag)
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
                mediaPath = urllib.parse.unquote(href[7:])
                media['media'] = mediaPath
            else:
                mediaPath = href[4:]
                media['media'] = mediaPath
            content += '[sound:%s]' % os.path.basename(mediaPath)
        return {'content': content, 'media': media}

    def getNodeCrosslink(self, tag):
        """
        :param tag: tag to get the crosslink from
        :return: node id of the node the crosslink refers to
        """
        href = self.getNodeHyperlink(tag)
        if href and href.startswith('xmind:#'):
            return href[7:]
        else:
            return None

    def getNodeHyperlink(self, tag):
        """
        :param tag: tag to get the hyperlink from
        :return: node's raw hyperlink string
        """
        try:
            return tag['xlink:href']
        except (KeyError, TypeError):
            return None

    def getNodeImg(self, tag):
        """
        :param tag: Tag to get the image from
        :return: node's raw image string
        """
        try:
            return tag.find('xhtml:img', recursive=False)['xhtml:src']
        except (TypeError, AttributeError):
            return None

    def getNodeTitle(self, tag):
        """
        :param tag: Tag to get the title from
        :return: node's title, empty string if it has none
        """
        try:
            return tag.find('title', recursive=False).text
        except AttributeError:
            return ''

    def getTagById(self, tagId):
        """
        :param tagId: the id property of the tag
        :return: ???
        """
        try:
            return tuple(filter(lambda t: t['id'] == tagId, self.tagList))[0]
        except IndexError:
            return None

    def isEmptyNode(self, tag):
        """
        :param tag: tag to check for
        :return: True if node does not contain any title, image or hyperlink
        """
        if self.getNodeTitle(tag):
            return False
        if self.getNodeImg(tag):
            return False
        if self.getNodeHyperlink(tag):
            return False
        return True
