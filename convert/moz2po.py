#!/usr/bin/env python
# 
# Copyright 2002, 2003 Zuza Software Foundation
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

"""Converts Mozilla .dtd and .properties files to Gettext .po files"""

import os.path
from translate.convert import dtd2po
from translate.convert import prop2po
from translate.storage import xpi
from translate import __version__
from translate.convert import convert

def main():
  formats = {("dtd", "dtd"): ("dtd.po", dtd2po.convertdtd),
             ("properties", "properties"): ("properties.po", prop2po.convertprop),
             "dtd": ("dtd.po", dtd2po.convertdtd),
             "properties": ("properties.po", prop2po.convertprop),
             (None, "*"): ("*", convert.copytemplate),
             ("*", "*"): ("*", convert.copyinput),
             "*": ("*", convert.copyinput)}
  parser = convert.ArchiveConvertOptionParser(formats, usetemplates=True, usepots=True, description=__doc__, archiveformats={"xpi": xpi.XpiFile})
  parser.passthrough.append("pot")
  parser.run()

