#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2009 Zuza Software Foundation
#
# This file is part of translate.
#
# translate is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# translate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with translate; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Class that manages subtitle files for translation

   This class makes use of the subtitle functionality of L{gaupol}
   @see: gaupo/agents/open.py::open_main

   a patch to gaupol is required to open utf-8 files successfully
"""

from StringIO import StringIO

import gaupol

from translate.storage import base

class SubtitleUnit(base.TranslationUnit):
    """A subtitle entry that is translatable"""

    def __init__(self, source=None, encoding="utf_8"):
        self._start = None
        self._end = None
        if source:
            self.source = source
        super(SubtitleUnit, self).__init__(source)

    def getlocations(self):
        return ["%s-->%s" % (self._start, self._end)]

class SubtitleFile(base.TranslationStore):
    """A subtitle file"""
    UnitClass = SubtitleUnit
    def __init__(self, inputfile=None, unitclass=UnitClass):
        """construct an Subtitle file, optionally reading in from inputfile."""
        self.UnitClass = unitclass
        base.TranslationStore.__init__(self, unitclass=unitclass)
        self.units = []
        self.filename = None
        self._subtitlefile = None
        self._encoding = 'utf-8'
        if inputfile is not None:
            self._parsefile(inputfile)

    def __str__(self):
        subtitles = []
        for unit in self.units:
            subtitle = gaupol.subtitle.Subtitle()
            subtitle.main_text = unit.target or unit.source
            subtitle.start = unit._start
            subtitle.end = unit._end
            subtitles.append(subtitle)
        output = StringIO()
        self._subtitlefile.write_to_file(subtitles, gaupol.documents.MAIN, output)
        return output.getvalue().encode(self._subtitlefile.encoding)

    def _parse(self):
        self._encoding = gaupol.encodings.detect(self.filename)
        if self._encoding == 'ascii':
            self._encoding = 'utf_8'
        self._format = gaupol.FormatDeterminer().determine(self.filename, self._encoding)
        self._subtitlefile = gaupol.files.new(self._format, self.filename, self._encoding)
        for subtitle in self._subtitlefile.read():
            newunit = self.addsourceunit(subtitle.main_text)
            newunit._start = subtitle.start
            newunit._end =  subtitle.end
            newunit.addnote("visible for %d seconds" % subtitle.duration_seconds, "developer")
            #FIXME: add location based on start?

    def _parsefile(self, storefile):
        if hasattr(storefile, 'name'):
            self.filename = storefile.name
            storefile.close()
        elif hasattr(storefile, 'filename'):
            self.filename = storefile.filename
            storefile.close()
        elif isinstance(storefile, basestring):
            self.filename = storefile
        if self.filename:
            self._parse()

    @classmethod
    def parsefile(cls, storefile):
        """parse the given file"""
        newstore = cls()
        newstore._parsefile(storefile)
        return newstore

    @classmethod
    def parsestring(cls, storestring):
        # Gaupol does not allow parsing from strings

        #FIXME: maybe we can write to a temporary file?
        raise NotImplementedError

    def parse(self, data):
        # Gaupol does not allow parsing from strings
        raise NotImplementedError
