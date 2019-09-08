#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.notes
    ~~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import xconst

from xmixin import TopicMixinElement


class NotesElement(TopicMixinElement):
    TAG_NAME = xconst.TAG_NOTES

    def __init__(self, node=None, ownerTopic=None):
        super(NotesElement, self).__init__(node, ownerTopic)

    def getContent(self, format=xconst.PLAIN_FORMAT_NOTE):
        """ Get notes content

        :parma format:  specified returned content format, plain text
                        by default.
        """

        content = self.getFirstChildNodeByTagName(format)

        if not content:
            return

        if format is xconst.PLAIN_FORMAT_NOTE:
            content = PlainNotes(node=content, ownerTopic=self.getOwnerTopic())
        else:
            raise Exception("Only support plain text notes right now")

        return content.getTextContent()


class _NoteContentElement(TopicMixinElement):
    def __init__(self, node=None, ownerTopic=None):
        super(_NoteContentElement, self).__init__(node, ownerTopic)

    def getFormat(self):
        return self.getImplementation().tagName


class PlainNotes(_NoteContentElement):
    """ Plain text notes

    :param content: utf8 plain text.
    :param node:    `xml.dom.Element` object`
    :param ownerTopic:  `xmind.core.topic.TopicElement` object

    """

    TAG_NAME = xconst.PLAIN_FORMAT_NOTE

    def __init__(self, content=None, node=None, ownerTopic=None):
        super(PlainNotes, self).__init__(node, ownerTopic)
        if content is not None:
            self.setTextContent(content)

    def setContent(self, content):
        self.setTextContent(content)
