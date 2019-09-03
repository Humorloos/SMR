#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.title
    ~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import xconst

from xmixin import WorkbookMixinElement


class TitleElement(WorkbookMixinElement):
    TAG_NAME = xconst.TAG_TITLE

    def __init__(self, node, ownerWorkbook):
        super(TitleElement, self).__init__(node, ownerWorkbook)

