# class for reading and writing xmind files

import os
import urllib.parse
import re
import zipfile

from bs4 import BeautifulSoup


class XManager:
    def __init__(self, file):
        self.xZip = zipfile.ZipFile(file, 'r')
        self.file = file
        self.soup = BeautifulSoup(self.xZip.read('content.xml'),
                                  features='html.parser')
        self.sheets = dict()
        for sheet in self.soup('sheet'):
            sheetTitle = sheet('title', recursive=False)[0].text
            self.sheets[sheetTitle] = {'tag': sheet, 'nodes': sheet('topic')}

    def getAttachment(self, identifier, dir):
        # extract attachment to anki media directory
        self.xZip.extract(identifier, dir)
        # get image from subdirectory attachments in mediaDir
        return os.path.join(dir, identifier)

    def getChildnodes(self, tag):
        """
        :param tag: the tag to get the childnodes for
        :return: childnodes as tags, empty list if it doesn't have any
        """
        try:
            return tag.find('children', recursive=False).find(
                'topics', recursive=False)('topic', recursive=False)
        except AttributeError:
            return []

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

        # if necessary add image
        attachment = self.getNodeImg(tag=tag)
        if attachment:
            if content != '':
                content += '<br>'
            fileName = re.search('/.*', attachment).group()[1:]
            content += '<img src="%s">' % fileName
            media['image'] = attachment[4:]

        # If the node contains a link to another node, add the text of that
        # node. Use Beautifulsoup because minidom can't find nodes by attributes
        if href and href.startswith('xmind:#'):
            crosslinkTag = self.getTagById(tagId=href[7:])
            crosslinkTitle = self.getNodeTitle(crosslinkTag)
            if not content:
                content = crosslinkTitle

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
        :return: the tag containing the Id
        """
        try:
            return tuple(filter(lambda t: t['id'] == tagId, self.tag_list()))[0]
        except IndexError:
            # TODO: Warn if the node is not found
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

    def isQuestionNode(self, tag, level=0):
        # If the Tag is the root topic, return true if the length of the path is odd
        if tag.parent.name == 'sheet':
            return level % 2 == 1
        # Else add one to the path length and test again
        return self.isQuestionNode(tag.parent.parent.parent, level + 1)

    def is_anki_question(self, tag):
        if not self.isQuestionNode(tag):
            return False
        if self.isEmptyNode(tag):
            return False
        children = self.getChildnodes(tag)
        if len(children) == 0:
            return False
        for child in children:
            if not self.isEmptyNode(child):
                return True
        return False

    def content_sheets(self):
        return [k for k in self.sheets.keys() if k != 'ref']

    def get_remote(self):
        content_keys = self.content_sheets()
        content_sheets = [self.sheets[s] for s in content_keys]
        sheets = {s['tag']['id']: {'xMod': s['tag']['timestamp'], 'questions': {
            t['id']: {'xMod': t['timestamp'], 'answers': {
                a['id']: {'xMod': a['timestamp']} for a in
                self.getChildnodes(t) if not self.isEmptyNode(a)}} for t in
            s['nodes'] if self.is_anki_question(t)}} for s in content_sheets}
        docMod = self.soup.find('xmap-content')['timestamp']
        remote = {'file': self.file, 'xMod': docMod, 'sheets': sheets}
        print()

    def tag_list(self):
        # Nested list comprehension explained:
        # https://stackoverflow.com/questions/20639180/explanation-of-how-nested-list-comprehension-works
        return [t for s in self.sheets for t in self.sheets[s]['nodes']]
