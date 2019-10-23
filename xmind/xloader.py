#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
    xmind.core.loader
    ~~~~~~~~~~~~~~~~~

    :copyright:
    :license:

"""

__author__ = "aiqi@xmind.net <Woody Ai>"

from . import xconst
from . import xutils

from .xworkbook import WorkbookDocument


class WorkbookLoader(object):
    def __init__(self, path):
        """ Load XMind workbook from given path

        :param path:    path to XMind file. If not an existing file,
                        will not raise an exception.

        """
        super(WorkbookLoader, self).__init__()
        self._input_source = xutils.get_abs_path(path)

        file_name, ext = xutils.split_ext(self._input_source)

        if ext != xconst.XMIND_EXT:
            raise Exception("The XMind filename is missing the '%s' extension!" % xconst.XMIND_EXT)

        # Input Stream
        self._content_stream = None

        try:
            with xutils.extract(self._input_source) as input_stream:
                for stream in input_stream.namelist():
                    if stream == xconst.CONTENT_XML:
                        self._content_stream = xutils.parse_dom_string(
                            input_stream.read(stream))
        except:
            pass

    def get_workbook(self):
        """ Parse XMind file to `WorkbookDocument` object and return
        """
        content = self._content_stream
        path = self._input_source

        workbook = WorkbookDocument(content, path)
        return workbook

