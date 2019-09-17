#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.title
    ~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

from XmindImport.xmind import xconst

from XmindImport.xmind.xmixin import WorkbookMixinElement


class TitleElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_TITLE

    def __init__(self, node, ownerWorkbook):
        super(TitleElement, self).__init__(node, ownerWorkbook)

