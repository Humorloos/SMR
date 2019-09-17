#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.saver
    ~~~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

import codecs

from XmindImport.xmind import xconst
from XmindImport.xmind import xutils


class WorkbookSaver(object):
    def __init__(self, workbook):
        """ Save `WorkbookDocument` as XMind file.

        :param workbook: `WorkbookDocument` object

        """
        self._workbook = workbook

    def _get_content(self):
        content_path = xutils.join_path(xutils.temp_dir(), xconst.CONTENT_XML)

        with codecs.open(content_path, "w", encoding="utf-8") as f:
            self._workbook.output(f)

        return content_path

    def save(self, path=None):
        """
        Save the workbook to the given path. If the path is not given, then
        will save to the path set in workbook.
        """
        path = path or self._workbook.get_path()

        if not path:
            raise Exception("Please specify a filename for the XMind file")

        path = xutils.get_abs_path(path)

        file_name, ext = xutils.split_ext(path)

        if ext != xconst.XMIND_EXT:
            raise Exception("XMind filenames require a '%s' extension" % xconst.XMIND_EXT)

        content = self._get_content()

        f=xutils.compress(path)
        f.write(content, xconst.CONTENT_XML)

