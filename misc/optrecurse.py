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

import sys
import os.path
import fnmatch
try:
  import optparse
  if optparse.__version__ < "1.4.1+":
    raise ImportError("optparse version not compatible")
except ImportError:
  from translate.misc import optparse
from translate.misc import progressbar
from translate import __version__
try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO

class RecursiveOptionParser(optparse.OptionParser, object):
  """a specialized Option Parser for recursing through directories..."""
  def __init__(self, formats, usetemplates=False, description=None):
    """construct the specialized Option Parser"""
    optparse.OptionParser.__init__(self, version="%prog "+__version__.ver, description=description)
    self.setprogressoptions()
    self.setformats(formats, usetemplates)
    self.setpsycooption()
    self.passthrough = []

  def setpsycooption(self):
    psycooption = optparse.Option(None, "--psyco", dest="psyco", default=None,
                    choices=("none", "full", "profile"), metavar="PSYCO",
                    help="use psyco to speed up the operation (set mode)")
    self.define_option(psycooption)

  def usepsyco(self, options):
    # options.psyco == None means the default, which is "full", but don't give a warning...
    # options.psyco == "none" means don't use psyco at all...
    if options.psyco == "none":
      return
    try:
      import psyco
    except Exception, e:
      if options.psyco is not None:
        self.warning("psyco unavailable: %s" % e)
      return
    if options.psyco is None:
      options.psyco = "full"
    if options.psyco == "full":
      psyco.full()
    elif options.psyco == "profile":
      psyco.profile()
    # tell psyco the functions it cannot compile, to prevent warnings
    import encodings
    psyco.cannotcompile(encodings.search_function)

  def set_usage(self, usage=None):
    """sets the usage string - if usage not given, uses getusagestring for each option"""
    if usage is None:
      self.usage = "%prog " + " ".join([self.getusagestring(option) for option in self.option_list])
    else:
      super(RecursiveOptionParser, self).set_usage(usage)

  def warning(self, msg):
    """Print a warning message incorporating 'msg' to stderr and exit."""
    print >>sys.stderr, "\n%s: warning: %s" % (optparse.get_prog_name(), msg)

  def getusagestring(self, option):
    """returns the usage string for the given option"""
    optionstring = "|".join(option._short_opts + option._long_opts)
    if getattr(option, "optionalswitch", False):
      optionstring = "[%s]" % optionstring
    if option.metavar:
      optionstring += " " + option.metavar
    if getattr(option, "required", False):
      return optionstring
    else:
      return "[%s]" % optionstring

  def define_option(self, option):
    """defines the given option, replacing an existing one of the same short name if neccessary..."""
    for short_opt in option._short_opts:
      if self.has_option(short_opt):
        self.remove_option(short_opt)
    for long_opt in option._long_opts:
      if self.has_option(long_opt):
        self.remove_option(long_opt)
    self.add_option(option)

  def setformats(self, formats, usetemplates):
    """sets the format options using the given format dictionary
    formats' keys should be
    - single strings (or 1-tuples) containing an input format (if not usetemplates)
    - tuples containing an input format and template format (if usetemplates)
    - formats can be None to indicate what to do with standard input
    formats' values should be tuples of outputformat (string) and processor method"""
    inputformats = []
    outputformats = []
    templateformats = []
    self.outputoptions = {}
    self.usetemplates = usetemplates
    for formatgroup, outputoptions in formats.iteritems():
      if isinstance(formatgroup, (str, unicode)) or formatgroup is None:
        formatgroup = (formatgroup, )
      if not isinstance(formatgroup, tuple):
        raise ValueError("formatgroups must be tuples or None/str/unicode")
      if len(formatgroup) < 1 or len(formatgroup) > 2:
        raise ValueError("formatgroups must be tuples of length 1 or 2")
      if len(formatgroup) == 1:
        formatgroup += (None, )
      inputformat, templateformat = formatgroup
      if not isinstance(outputoptions, tuple) or len(outputoptions) != 2:
        raise ValueError("output options must be tuples of length 2")
      outputformat, processor = outputoptions
      if not inputformat in inputformats: inputformats.append(inputformat)
      if not outputformat in outputformats: outputformats.append(outputformat)
      if not templateformat in templateformats: templateformats.append(templateformat)
      self.outputoptions[(inputformat, templateformat)] = (outputformat, processor)
    self.inputformats = inputformats
    inputformathelp = self.getformathelp(inputformats)
    inputoption = optparse.Option("-i", "--input", dest="input", default=None, metavar="INPUT",
                    help="read from INPUT in %s" % (inputformathelp))
    inputoption.optionalswitch = True
    inputoption.required = True
    self.define_option(inputoption)
    excludeoption = optparse.Option("-x", "--exclude", dest="exclude", action="append",
                    type="string", default=[], metavar="EXCLUDE",
                    help="exclude names matching EXCLUDE from input paths")
    self.define_option(excludeoption)
    outputformathelp = self.getformathelp(outputformats)
    outputoption = optparse.Option("-o", "--output", dest="output", default=None, metavar="OUTPUT",
                    help="write to OUTPUT in %s" % (outputformathelp))
    outputoption.optionalswitch = True
    outputoption.required = True
    self.define_option(outputoption)
    if self.usetemplates:
      self.templateformats = templateformats
      templateformathelp = self.getformathelp(self.templateformats)
      templateoption = optparse.Option("-t", "--template", dest="template", default=None, metavar="TEMPLATE",
                  help="read from TEMPLATE in %s" % (templateformathelp))
      self.define_option(templateoption)

  def setprogressoptions(self):
    """sets the progress options"""
    self.progresstypes = {"none": progressbar.NoProgressBar, "dots": progressbar.DotsProgressBar,
                          "bar": progressbar.HashProgressBar, "verbose": progressbar.VerboseProgressBar}
    progressoption = optparse.Option(None, "--progress", dest="progress", default="bar",
                      choices = self.progresstypes.keys(), metavar="PROGRESS",
                      help="show progress as: %s" % (", ".join(self.progresstypes)))
    self.define_option(progressoption)

  def getformathelp(self, formats):
    """make a nice help string for describing formats..."""
    if None in formats:
      formats = filter(lambda format: format is not None, formats)
    if len(formats) == 0:
      return ""
    elif len(formats) == 1:
      return "%s format" % (", ".join(formats))
    else:
      return "%s formats" % (", ".join(formats))

  def isrecursive(self, fileoption):
    """checks if fileoption is a recursive file"""
    if fileoption is None:
      return False
    elif isinstance(fileoption, list):
      return True
    else:
      return os.path.isdir(fileoption)

  def parse_args(self, args=None, values=None):
    """parses the command line options, handling implicit input/output args"""
    (options, args) = super(RecursiveOptionParser, self).parse_args(args, values)
    # some intelligent as to what reasonable people might give on the command line
    if args and not options.input:
      if len(args) > 1:
        options.input = args[:-1]
        args = args[-1:]
      else:
        options.input = args[0]
        args = []
    if args and not options.output:
      options.output = args[-1]
      args = args[:-1]
    if args:
      self.error("You have used an invalid combination of --input, --output and freestanding args")
    if isinstance(options.input, list) and len(options.input) == 1:
      options.input = options.input[0]
    if options.input is None:
      self.error("You need to give an inputfile or use - for stdin ; use --help for full usage instructions")
    elif options.input == '-':
      options.input = None
    return (options, args)

  def getpassthroughoptions(self, options):
    """get the options required to pass to the filtermethod..."""
    passthroughoptions = {}
    for optionname in dir(options):
      if optionname in self.passthrough:
        passthroughoptions[optionname] = getattr(options, optionname)
    return passthroughoptions

  def getoutputoptions(self, options, inputpath, templatepath):
    """works out which output format and processor method to use..."""
    if inputpath:
      inputbase, inputext = self.splitinputext(inputpath)
    else:
      inputext = None
    if templatepath:
      templatebase, templateext = self.splittemplateext(templatepath)
    else:
      templateext = None
    if (inputext, templateext) in options.outputoptions:
      return options.outputoptions[inputext, templateext]
    elif (inputext, "*") in options.outputoptions:
      outputformat, fileprocessor = options.outputoptions[inputext, "*"]
    elif ("*", templateext) in options.outputoptions:
      outputformat, fileprocessor = options.outputoptions["*", templateext]
    elif ("*", "*") in options.outputoptions:
      outputformat, fileprocessor = options.outputoptions["*", "*"]
    elif (inputext, None) in options.outputoptions:
      return options.outputoptions[inputext, None]
    elif (None, templateext) in options.outputoptions:
      return options.outputoptions[None, templateext]
    elif ("*", None) in options.outputoptions:
      outputformat, fileprocessor = options.outputoptions["*", None]
    elif (None, "*") in options.outputoptions:
      outputformat, fileprocessor = options.outputoptions[None, "*"]
    else:
      if self.usetemplates:
        raise ValueError("could not find outputoptions for inputext %s, templateext %s" % (inputext, templateext))
      else:
        raise ValueError("could not find outputoptions for inputext %s" % inputext)
    if outputformat == "*":
      if inputext:
        outputformat = inputext
      elif templateext:
        outputformat = templateext
      else:
        if self.usetemplates:
          raise ValueError("could not find output format for inputext %s, templateext %s" % (inputext, templateext))
        else:
          raise ValueError("could not find output format for inputext %s" % inputext)
    return outputformat, fileprocessor

  def initprogressbar(self, allfiles, options):
    """sets up a progress bar appropriate to the options and files"""
    if options.progress in ('bar', 'verbose'):
      self.progressbar = self.progresstypes[options.progress](0, len(allfiles))
      print "processing %d files..." % len(allfiles)
    else:
      self.progressbar = self.progresstypes[options.progress]()

  def getfullinputpath(self, options, inputpath):
    """gets the absolute path to an input file"""
    if options.input:
      return os.path.join(options.input, inputpath)
    else:
      return inputpath

  def getfulloutputpath(self, options, outputpath):
    """gets the absolute path to an output file"""
    if options.recursiveoutput and options.output:
      return os.path.join(options.output, outputpath)
    else:
      return outputpath

  def getfulltemplatepath(self, options, templatepath):
    """gets the absolute path to a template file"""
    if not options.recursivetemplate:
      return templatepath
    elif templatepath is not None and self.usetemplates and options.template:
      return os.path.join(options.template, templatepath)
    else:
      return None

  def run(self):
    """parses the arguments, and runs recursiveprocess with the resulting options..."""
    (options, args) = self.parse_args()
    # this is so derived classes can modify the inputformats etc based on the options
    options.inputformats = self.inputformats
    options.outputoptions = self.outputoptions
    self.usepsyco(options)
    self.recursiveprocess(options)

  def recursiveprocess(self, options):
    """recurse through directories and process files"""
    if self.isrecursive(options.input):
      if not self.isrecursive(options.output):
        try:
          self.warning("Output directory does not exist. Attempting to create")
          os.mkdir(options.output)
        except:
          self.error(optparse.OptionValueError("Output directory does not exist, attempt to create failed"))
      if isinstance(options.input, list):
        inputfiles = self.recurseinputfilelist(options)
      else:
        inputfiles = self.recurseinputfiles(options)
    else:
      if options.input:
        inputfiles = [os.path.basename(options.input)]
        options.input = os.path.dirname(options.input)
      else:
        inputfiles = [options.input]
    options.recursiveoutput = self.isrecursive(options.output)
    options.recursivetemplate = self.usetemplates and self.isrecursive(options.template)
    self.initprogressbar(inputfiles, options)
    for inputpath in inputfiles:
      templatepath = self.gettemplatename(options, inputpath)
      outputformat, fileprocessor = self.getoutputoptions(options, inputpath, templatepath)
      fullinputpath = self.getfullinputpath(options, inputpath)
      fulltemplatepath = self.getfulltemplatepath(options, templatepath)
      outputpath = self.getoutputname(options, inputpath, outputformat)
      fulloutputpath = self.getfulloutputpath(options, outputpath)
      if options.recursiveoutput and outputpath:
        self.checkoutputsubdir(options, os.path.dirname(outputpath))
      try:
        success = self.processfile(fileprocessor, options, fullinputpath, fulloutputpath, fulltemplatepath)
      except Exception:
        self.warning("Error processing: input %s, output %s, template %s" % (fullinputpath, fulloutputpath, fulltemplatepath))
        raise
      self.reportprogress(inputpath, success)
    del self.progressbar

  def openinputfile(self, options, fullinputpath):
    """opens the input file"""
    if fullinputpath is None:
      return sys.stdin
    return open(fullinputpath, 'r')

  def openoutputfile(self, options, fulloutputpath):
    """opens the output file"""
    if fulloutputpath is None:
      return sys.stdout
    return open(fulloutputpath, 'w')

  def opentempoutputfile(self, options, fulloutputpath):
    """opens a temporary output file"""
    return StringIO()

  def finalizetempoutputfile(self, options, outputfile, fulloutputpath):
    """write the temp outputfile to its final destination"""
    outputfile.reset()
    outputstring = outputfile.read()
    outputfile = self.openoutputfile(options, fulloutputpath)
    outputfile.write(outputstring)
    outputfile.close()

  def opentemplatefile(self, options, fulltemplatepath):
    """opens the template file (if required)"""
    if fulltemplatepath is not None:
      if os.path.isfile(fulltemplatepath):
        return open(fulltemplatepath, 'r')
      else:
        self.warning("missing template file %s" % fulltemplatepath)
    return None

  def processfile(self, fileprocessor, options, fullinputpath, fulloutputpath, fulltemplatepath):
    """process an individual file"""
    inputfile = self.openinputfile(options, fullinputpath)
    if fulloutputpath and fulloutputpath in (fullinputpath, fulltemplatepath):
      outputfile = self.opentempoutputfile(options, fulloutputpath)
      tempoutput = True
    else:
      outputfile = self.openoutputfile(options, fulloutputpath)
      tempoutput = False
    templatefile = self.opentemplatefile(options, fulltemplatepath)
    passthroughoptions = self.getpassthroughoptions(options)
    if fileprocessor(inputfile, outputfile, templatefile, **passthroughoptions):
      if tempoutput:
        self.warning("writing to temporary output...")
        self.finalizetempoutputfile(options, outputfile, fulloutputpath)
      return True
    else:
      # remove the file if it is a file (could be stdout etc)
      if fulloutputpath and os.path.isfile(fulloutputpath):
        outputfile.close()
        os.unlink(fulloutputpath)
      return False

  def reportprogress(self, filename, success):
    """shows that we are progressing..."""
    self.progressbar.amount += 1
    self.progressbar.show(filename)

  def mkdir(self, parent, subdir):
    """makes a subdirectory (recursively if neccessary)"""
    if not os.path.isdir(parent):
      raise ValueError("cannot make child directory %r if parent %r does not exist" % (subdir, parent))
    currentpath = parent
    subparts = subdir.split(os.sep)
    for part in subparts:
      currentpath = os.path.join(currentpath, part)
      if not os.path.isdir(currentpath):
        os.mkdir(currentpath)

  def checkoutputsubdir(self, options, subdir):
    """checks to see if subdir under options.output needs to be created, creates if neccessary"""
    fullpath = os.path.join(options.output, subdir)
    if not os.path.isdir(fullpath):
      self.mkdir(options.output, subdir)

  def isexcluded(self, options, inputpath):
    """checks if this path has been excluded"""
    basename = os.path.basename(inputpath)
    for excludename in options.exclude:
      if fnmatch.fnmatch(basename, excludename):
        return True
    return False

  def recurseinputfilelist(self, options):
    """use a list of files, and find a common base directory for them"""
    # find a common base directory for the files to do everything relative to
    commondir = os.path.dirname(os.path.commonprefix(options.input))
    inputfiles = []
    for inputfile in options.input:
      if self.isexcluded(options, inputfile):
        continue
      if inputfile.startswith(commondir+os.sep):
        inputfiles.append(inputfile.replace(commondir+os.sep, "", 1))
      else:
        inputfiles.append(inputfile.replace(commondir, "", 1))
    options.input = commondir
    return inputfiles

  def recurseinputfiles(self, options):
    """recurse through directories and return files to be processed..."""
    dirstack = ['']
    join = os.path.join
    inputfiles = []
    while dirstack:
      top = dirstack.pop(-1)
      names = os.listdir(join(options.input, top))
      dirs = []
      for name in names:
        inputpath = join(top, name)
        if self.isexcluded(options, inputpath):
          continue
        fullinputpath = self.getfullinputpath(options, inputpath)
        # handle directories...
        if os.path.isdir(fullinputpath):
          dirs.append(inputpath)
        elif os.path.isfile(fullinputpath):
          if not self.isvalidinputname(options, name):
            # only handle names that match recognized input file extensions
            continue
          inputfiles.append(inputpath)
      # make sure the directories are processed next time round...
      dirs.reverse()
      dirstack.extend(dirs)
    return inputfiles

  def splitext(self, pathname):
    """splits into name and ext, and removes the extsep"""
    root, ext = os.path.splitext(pathname)
    ext = ext.replace(os.extsep, "", 1)
    return (root, ext)

  def splitinputext(self, inputpath):
    """splits an inputpath into name and extension"""
    return self.splitext(inputpath)

  def splittemplateext(self, templatepath):
    """splits a templatepath into name and extension"""
    return self.splitext(templatepath)

  def templateexists(self, options, templatepath):
    """returns whether the given template exists..."""
    fulltemplatepath = self.getfulltemplatepath(options, templatepath)
    return os.path.isfile(fulltemplatepath)

  def gettemplatename(self, options, inputname):
    """gets an output filename based on the input filename"""
    if not self.usetemplates: return None
    if not inputname or not options.recursivetemplate: return options.template
    inputbase, inputext = self.splitinputext(inputname)
    if options.template:
      for inputext1, templateext1 in options.outputoptions:
        if inputext == inputext1:
          if templateext1:
            templatepath = inputbase + os.extsep + templateext1
            if self.templateexists(options, templatepath):
              return templatepath
      if "*" in options.inputformats:
        for inputext1, templateext1 in options.outputoptions:
          if (inputext == inputext1) or (inputext1 == "*"):
            if templateext1 == "*":
              templatepath = inputname
              if self.templateexists(options, templatepath):
                return templatepath
            elif templateext1:
              templatepath = inputbase + os.extsep + templateext1
              if self.templateexists(options, templatepath):
                return templatepath
    return None

  def getoutputname(self, options, inputname, outputformat):
    """gets an output filename based on the input filename"""
    if not inputname or not options.recursiveoutput: return options.output
    inputbase, inputext = self.splitinputext(inputname)
    return inputbase + os.extsep + outputformat

  def isvalidinputname(self, options, inputname):
    """checks if this is a valid input filename"""
    inputbase, inputext = self.splitinputext(inputname)
    return (inputext in options.inputformats) or ("*" in options.inputformats)

