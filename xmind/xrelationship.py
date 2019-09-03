#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.relationship
    ~~~~~~~~~~~~~~~~~~~


    :copyright:
    :license:
"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import xconst

from xmixin import WorkbookMixinElement
from xtopic import TopicElement
from xtitle import TitleElement


class RelationshipElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_RELATIONSHIP

    def __init__(self, node, ownerWorkbook):
        super(RelationshipElement, self).__init__(node, ownerWorkbook)

        self.addIdAttribute(xconst.ATTR_ID)

    def _get_title(self):
        return self.getFirstChildNodeByTagName(xconst.TAG_TITLE)

    def _find_end_point(self, id):
        owner_workbook = self.getOwnerWorkbook()
        if owner_workbook is None:
            return

        end_point = owner_workbook.getElementById(id)
        if end_point is None:
            return

        if end_point.tagName == xconst.TAG_TOPIC:
            return TopicElement(end_point, owner_workbook)

    # FIXME: Convert the following to getter/setter

    def getEnd1ID(self):
        return self.getAttribute(xconst.ATTR_END1)

    def setEnd1ID(self, id):
        self.setAttribute(xconst.ATTR_END1, id)
        self.updateModifiedTime()

    def getEnd2ID(self):
        return self.getAttribute(xconst.ATTR_END2)

    def setEnd2ID(self, id):
        self.setAttribute(xconst.ATTR_END2, id)
        self.updateModifiedTime()

    def getEnd1(self, end1_id):
        return self._find_end_point(end1_id)

    def getEnd2(self, end2_id):
        return self._find_end_point(end2_id)

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

        self.updateModifiedTime()


class RelationshipsElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_RELATIONSHIPS

    def __init__(self, node, ownerWorkbook):
        super(RelationshipsElement, self).__init__(node, ownerWorkbook)

    
    def getRelationships(self):
        """
        List all relationships
        """
        relationships = []
        ownerWorkbook = self.getOwnerWorkbook()
        for t in self.getChildNodesByTagName(xconst.TAG_RELATIONSHIP):
            relationships.append(TopicElement(t, ownerWorkbook))

        return relationships


