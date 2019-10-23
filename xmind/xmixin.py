#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.mixin
    ~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

from . import xconst
from .xcore import Element
from . import xutils


class WorkbookMixinElement(Element):
    """
    """
    def __init__(self, node, ownerWorkbook):
        super(WorkbookMixinElement, self).__init__(node)
        self._owner_workbook = ownerWorkbook
        self.registOwnerWorkbook()

    def registOwnerWorkbook(self):
        if self._owner_workbook:
            self.setOwnerDocument(self._owner_workbook.getOwnerDocument())

    def getOwnerWorkbook(self):
        return self._owner_workbook

    def setOwnerWorkbook(self, workbook):
        if not self._owner_workbook:
            self._owner_workbook = workbook

    def getModifiedTime(self):
        timestamp = self.getAttribute(xconst.ATTR_TIMESTAMP)
        if timestamp:
            return xutils.readable_time(timestamp)

    def setModifiedTime(self, time):
        self.setAttribute(xconst.ATTR_TIMESTAMP, int(time))

    def updateModifiedTime(self):
        self.setModifiedTime(xutils.get_current_time())

    def getID(self):
        return self.getAttribute(xconst.ATTR_ID)


class TopicMixinElement(Element):
    def __init__(self, node, ownerTopic):
        super(TopicMixinElement, self).__init__(node)
        self._owner_topic = ownerTopic

    def getOwnerTopic(self):
        return self._owner_topic

    def getOwnerSheet(self):
        if not self._owner_topic:
            return

        return self._owner_topic.getOwnerSheet()

    def getOwnerWorkbook(self):
        if not self._owner_topic:
            return

        return self._owner_topic.getOwnerWorkbook()
