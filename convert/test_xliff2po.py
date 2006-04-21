#!/usr/bin/env python

from translate.convert import xliff2po
from translate.storage import po

class TestXLIFF2PO:
    xliffskeleton = '''<?xml version="1.0" ?>
<xliff version="1.1" xmlns="urn:oasis:names:tc:xliff:document:1.1">
  <file original="filename.po" source-language="en-US" datatype="po">
    <body>
        %s
    </body>
  </file>
</xliff>'''

    def xliff2po(self, xliffsource):
        """helper that converts xliff source to po source without requiring files"""
	convertor = xliff2po.xliff2po()
	outputpo = convertor.convertfile(xliffsource)
        print "The generated po:"
        print str(outputpo)
        return outputpo
	
    def test_minimal(self):
        minixlf = self.xliffskeleton % '''<trans-unit>
        <source>red</source>
        <target>rooi</target>
      </trans-unit>'''
        pofile = self.xliff2po(minixlf)
        assert len(pofile.units) == 1
        assert pofile.translate("red") == "rooi"
        assert pofile.translate("bla") is None
 
    def test_basic(self):
        headertext = '''Project-Id-Version: program 2.1-branch
Report-Msgid-Bugs-To: 
POT-Creation-Date: 2006-01-09 07:15+0100
PO-Revision-Date: 2004-03-30 17:02+0200
Last-Translator: Zuza Software Foundation &lt;xxx@translate.org.za>
Language-Team: Afrikaans &lt;translate-discuss-xxx@lists.sourceforge.net>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit'''

        minixlf = (self.xliffskeleton % '''<trans-unit id="1" restype="x-gettext-domain-header" approved="no" xml:space="preserve">
  <source>%s</source>
  <target>%s</target>
  <note from="po-translator">Zulu translation of program ABC</note>
  </trans-unit>
  <trans-unit>
    <source>gras</source>
    <target>utshani</target>
  </trans-unit>''') % (headertext, headertext)

        pofile = self.xliff2po(minixlf)
        assert pofile.translate("gras") == "utshani"
        assert pofile.translate("bla") is None
        potext = str(pofile)
	assert potext.index('# Zulu translation of program ABC') == 0
	assert potext.index('msgid "gras"\n')
	assert potext.index('msgstr "utshani"\n')
        assert potext.index('MIME-Version: 1.0\\n')

    def test_translatorcomments(self):
        """Tests translator comments"""
        minixlf = self.xliffskeleton % '''<trans-unit>
        <source>nonsense</source>
        <target>matlhapolosa</target>
        <context-group name="po-entry" purpose="information">
            <context context-type="x-po-trancomment">Couldn't do
it</context>
        </context-group>
</trans-unit>'''
        pofile = self.xliff2po(minixlf)
        assert pofile.translate("nonsense") == "matlhapolosa"
        assert pofile.translate("bla") is None
        unit = pofile.units[0]
        assert unit.othercomments == ["# Couldn't do\n", "# it\n"]
        potext = str(pofile)
        assert potext.index("# Couldn't do\n# it\n") >= 0

    def test_autocomment(self):
        """Tests automatic comments"""
        minixlf = self.xliffskeleton % '''<trans-unit>
        <source>nonsense</source>
        <target>matlhapolosa</target>
        <context-group name="po-entry" purpose="information">
            <context context-type="x-po-autocomment">Note that this is
garbage</context>
        </context-group>
</trans-unit>'''
        pofile = self.xliff2po(minixlf)
        assert pofile.translate("nonsense") == "matlhapolosa"
        assert pofile.translate("bla") is None
        unit = pofile.units[0]
        assert unit.automaticcomments == ["#. Note that this is\n", "#. garbage\n"]
        potext = str(pofile)
        assert potext.index("#. Note that this is\n#. garbage\n") >= 0

    def test_locations(self):
        """Tests location comments (#:)"""
        minixlf = self.xliffskeleton % '''<trans-unit id="1">
        <source>nonsense</source>
        <target>matlhapolosa</target>
        <context-group name="po-reference" purpose="location">
            <context context-type="sourcefile">example.c</context>
            <context context-type="linenumber">123</context>
            </context-group>
        <context-group name="po-reference" purpose="location">
            <context context-type="sourcefile">place.py</context>
        </context-group>
</trans-unit>'''
        pofile = self.xliff2po(minixlf)
        assert pofile.translate("nonsense") == "matlhapolosa"
        assert pofile.translate("bla") is None
        unit = pofile.units[0]
        ids = unit.getids()
        assert len(ids) == 2
        assert "example.c:123" in ids
        assert "place.py" in ids

    def test_fuzzy(self):
        """Tests fuzzyness"""
        minixlf = self.xliffskeleton % '''<trans-unit approved="no">
            <source>book</source>
        </trans-unit>
        <trans-unit id="2" approved="yes">
            <source>nonsense</source>
            <target>matlhapolosa</target>
        </trans-unit>
        <trans-unit id="2" approved="no">
            <source>verb</source>
            <target state="needs-review-translation">lediri</target>
        </trans-unit>'''
        pofile = self.xliff2po(minixlf)
        assert pofile.translate("nonsense") == "matlhapolosa"
        assert pofile.translate("verb") == "lediri"
        assert pofile.translate("book") is None
        assert pofile.translate("bla") is None
        assert len(pofile.units) == 3
        #TODO: decide if this one should be fuzzy:
        #assert pofile.units[0].isfuzzy()
        assert not pofile.units[1].isfuzzy()
        assert pofile.units[2].isfuzzy()
        
