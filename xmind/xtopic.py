#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.topic
    ~~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import xconst

from XmindImport.xmind.xmixin import WorkbookMixinElement
from XmindImport.xmind.xtitle import TitleElement
from XmindImport.xmind.xposition import PositionElement
from XmindImport.xmind.xnotes import NotesElement, PlainNotes
from XmindImport.xmind.xmarkerref import MarkerRefElement, MarkerRefsElement
import xutils


def split_hyperlink(hyperlink):
    colon = hyperlink.find(":")
    if colon < 0:
        protocol = None
    else:
        protocol = hyperlink[:colon]

    hyperlink = hyperlink[colon + 1:]
    while hyperlink.startswith("/"):
        hyperlink = hyperlink[1:]

    return (protocol, hyperlink)


class TopicElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_TOPIC

    def __init__(self, node, ownerWorkbook):
        super(TopicElement, self).__init__(node, ownerWorkbook)

        self.addIdAttribute(xconst.ATTR_ID)

    def _get_title(self):
        return self.getFirstChildNodeByTagName(xconst.TAG_TITLE)

    def _get_markerrefs(self):
        return self.getFirstChildNodeByTagName(xconst.TAG_MARKERREFS)

    def _get_position(self):
        return self.getFirstChildNodeByTagName(xconst.TAG_POSITION)

    def _get_children(self):
        return self.getFirstChildNodeByTagName(xconst.TAG_CHILDREN)

    def _set_hyperlink(self, hyperlink):
        self.setAttribute(xconst.ATTR_HREF, hyperlink)
        #self.updateModifiedTime()

    def getOwnerSheet(self):
        parent = self.getParentNode()

        while parent and parent.tagName != xconst.TAG_SHEET:
            parent = parent.parentNode

        if not parent:
            return

        owner_workbook = self.getOwnerWorkbook()
        if not owner_workbook:
            return

        for sheet in owner_workbook.getSheets():
            if parent is sheet.getImplementation():
                return sheet

    def getTitle(self):
        title = self._get_title()
        if title:
            title = TitleElement(title, self.getOwnerWorkbook())
            return title.getTextContent()

    def setTitle(self, text):
        _title = self._get_title()
        title = TitleElement(_title, self.getOwnerWorkbook())
        title.setTextContent(text)

        if _title is None:
            self.appendChild(title)

        # self.updateModifiedTime()

    def getMarkers(self):
        refs = self._get_markerrefs()
        if not refs:
            return None
        tmp = MarkerRefsElement(refs, self.getOwnerWorkbook())
        markers = tmp.getChildNodesByTagName(xconst.TAG_MARKERREF)
        marker_list = []
        if markers:
            for i in markers:
                marker_list.append(MarkerRefElement(i, self.getOwnerWorkbook()))
        return marker_list

    def addMarker(self, markerId, replaceSameFamily = True):
        '''
        Adds a marker to this topic.
        @param markerId a MarkerID object indicating the marker to add
        @param replaceSameFamily. Whether an existing marker of the same
               family should be replaced or added (this would allow more
               than one marker of the same family).
        '''
        refs = self._get_markerrefs()
        if not refs:
            tmp = MarkerRefsElement(None, self.getOwnerWorkbook())
            self.appendChild(tmp)
        else:
            tmp = MarkerRefsElement(refs, self.getOwnerWorkbook())
        markers = tmp.getChildNodesByTagName(xconst.TAG_MARKERREF)
        if markers and replaceSameFamily:
            for m in markers:
                mre = MarkerRefElement(m, self.getOwnerWorkbook())
                # look for a marker of same familly
                if mre.getMarkerId().getFamily() == markerId.getFamily():
                    mre.setMarkerId(markerId)
                    return mre
        # not found so let's append it
        mre = MarkerRefElement(None, self.getOwnerWorkbook())
        mre.setMarkerId(markerId)
        tmp.appendChild(mre)
        return mre

    def setFolded(self):
        self.setAttribute(xconst.ATTR_BRANCH, xconst.VAL_FOLDED)

        # self.updateModifiedTime()

    def getPosition(self):
        """ Get a pair of integer located topic position.

        return (x, y) indicate x and y
        """
        position = self._get_position()
        if position is None:
            return

        position = PositionElement(position, self.getOwnerWorkbook())

        x = position.getX()
        y = position.getY()

        if x is None and y is None:
            return

        x = x or 0
        y = y or 0

        return (int(x), int(y))

    def setPosition(self, x, y):
        ownerWorkbook = self.getOwnerWorkbook()
        position = self._get_position()

        if not position:
            position = PositionElement(None, ownerWorkbook)
            self.appendChild(position)
        else:
            position = PositionElement(position, ownerWorkbook)

        position.setX(x)
        position.setY(y)

        # self.updateModifiedTime()

    def removePosition(self):
        position = self._get_position()
        if position is not None:
            self.getImplementation().removeChild(position)

        # self.updateModifiedTime()

    def getType(self):
        parent = self.getParentNode()
        if not parent:
            return

        if parent.tagName == xconst.TAG_SHEET:
            return xconst.TOPIC_ROOT

        if parent.tagName == xconst.TAG_TOPICS:
            topics = TopicsElement(parent, self.getOwnerWorkbook())
            return topics.getType()

    def getTopics(self, topics_type=xconst.TOPIC_ATTACHED):
        topic_children = self._get_children()

        if topic_children:
            topic_children = ChildrenElement(
                topic_children,
                self.getOwnerWorkbook())

            return topic_children.getTopics(topics_type)

    def getSubTopics(self, topics_type=xconst.TOPIC_ATTACHED):
        """ List all sub topics under current topic, If not sub topics,
        return empty list.
        """
        topics = self.getTopics(topics_type)
        if not topics:
            return []

        return topics.getSubTopics()

    def getSubTopicByIndex(self, index, topics_type=xconst.TOPIC_ATTACHED):
        """ Get sub topic by speicifeid index
        """
        sub_topics = self.getSubTopics(topics_type)
        if sub_topics is None:
            return

        if index < 0 or index >= len(sub_topics):
            return sub_topics

        return sub_topics[index]

    def addSubTopic(self, index=-1,
                    topics_type=xconst.TOPIC_ATTACHED):
        """
        Create empty sub topic to the current topic and return added sub topic
        @param index:   if index not given then passed topic will append to
                        sub topics list. Otherwise, index must be less than
                        length of sub topics list and insert passed topic
                        before given index.
        @param topics_tipe TOPIC_ATTACHED or TOPIC_DETACHED
        """
        ownerWorkbook = self.getOwnerWorkbook()
        topic = self.__class__(None, ownerWorkbook)

        topic_children = self._get_children()
        if not topic_children:
            topic_children = ChildrenElement(None, ownerWorkbook)
            self.appendChild(topic_children)
        else:
            topic_children = ChildrenElement(topic_children, ownerWorkbook)

        topics = topic_children.getTopics(topics_type)
        if not topics:
            topics = TopicsElement(None, ownerWorkbook)
            topics.setAttribute(xconst.ATTR_TYPE, topics_type)
            topic_children.appendChild(topics)

        topic_list = []
        for i in topics.getChildNodesByTagName(xconst.TAG_TOPIC):
            topic_list.append(TopicElement(i, ownerWorkbook))

        if index < 0 or len(topic_list) >= index:
            topics.appendChild(topic)
        else:
            topics.insertBefore(topic, topic_list[index])

        return topic

    def getIndex(self):
        parent = self.getParentNode()
        if parent and parent.tagName == xconst.TAG_TOPICS:
            index = 0
            for child in parent.childNodes:
                if self.getImplementation() == child:
                    return index
                index += 1
        return -1

    def getHyperlink(self):
        return self.getAttribute(xconst.ATTR_HREF)

    def setFileHyperlink(self, path):
        """
        Set file as topic hyperlink

        :param path: path of specified file

        """
        protocol, content = split_hyperlink(path)
        if not protocol:
            path = xconst.FILE_PROTOCOL + xutils.get_abs_path(path)

        self._set_hyperlink(path)

    def setTopicHyperlink(self, tid):
        """
        Set topic as topic hyperlink

        :param id: given topic's id

        """
        protocol, content = split_hyperlink(tid)
        if not protocol:
            if tid.startswith("#"):
                tid = tid[1:]

            tid = xconst.TOPIC_PROTOCOL + tid
        self._set_hyperlink(tid)

    def setURLHyperlink(self, url):
        """ Set URL as topic hyperlink

        :param url: HTTP URL to specified website

        """
        protocol, content = split_hyperlink(url)
        if not protocol:
            url = xconst.HTTP_PROTOCOL + content

        self._set_hyperlink(url)

    def getNotes(self):
        """
        Return `NotesElement` object` and invoke
        `NotesElement.getContent()` to get notes content.
        """

        notes = self.getFirstChildNodeByTagName(xconst.TAG_NOTES)

        if notes is not None:
            return NotesElement(notes, self)

    def _set_notes(self):
        notes = self.getNotes()

        if notes is None:
            notes = NotesElement(ownerTopic=self)
            self.appendChild(notes)

        return notes

    def setPlainNotes(self, content):
        """ Set plain text notes to topic

        :param content: utf8 plain text

        """
        notes = self._set_notes()
        new = PlainNotes(content, None, self)

        old = notes.getFirstChildNodeByTagName(new.getFormat())
        if old is not None:
            notes.getImplementation().removeChild(old)

        notes.appendChild(new)


class ChildrenElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_CHILDREN

    def __init__(self, node, ownerWorkbook):
        super(ChildrenElement, self).__init__(node, ownerWorkbook)

    def getTopics(self, topics_type):
        topics = self.iterChildNodesByTagName(xconst.TAG_TOPICS)
        for i in topics:
            t = TopicsElement(i, self.getOwnerWorkbook())
            if topics_type == t.getType():
                return t


class TopicsElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_TOPICS

    def __init__(self, node, ownerWorkbook):
        super(TopicsElement, self).__init__(node, ownerWorkbook)

    def getType(self):
        return self.getAttribute(xconst.ATTR_TYPE)

    def getSubTopics(self):
        """
        List all sub topics on the current topic
        """
        topics = []
        ownerWorkbook = self.getOwnerWorkbook()
        for t in self.getChildNodesByTagName(xconst.TAG_TOPIC):
            topics.append(TopicElement(t, ownerWorkbook))

        return topics

    def getSubTopicByIndex(self, index):
        """
        Get specified sub topic by index
        """
        sub_topics = self.getSubTopics()
        if index < 0 or index >= len(sub_topics):
            return sub_topics

        return sub_topics[index]
