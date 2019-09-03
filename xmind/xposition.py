#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.position
    ~~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import xconst

from xmixin import WorkbookMixinElement


class PositionElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_POSITION

    def __init__(self, node, ownerWorkbook):
        super(PositionElement, self).__init__(node, ownerWorkbook)

    # FIXME: These should be converted to getter/setters

    def getX(self):
        return self.getAttribute(xconst.ATTR_X)

    def getY(self):
        return self.getAttribute(xconst.ATTR_Y)

    def setX(self, x):
        self.setAttribute(xconst.ATTR_X, int(x))

    def setY(self, y):
        self.setAttribute(xconst.ATTR_Y, int(y))

