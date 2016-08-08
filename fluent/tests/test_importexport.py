# -*- coding: utf-8 -*-
from djangae.test import TestCase
import polib

from fluent.importexport import import_translations_from_po
from fluent.importexport import export_translations_to_po
from fluent.models import MasterTranslation, Translation


POFILE = '''# Test pofile
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2016-03-25 18:15+0000\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"Language: de\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

msgid "something something something something translate"
msgstr ""
'''

EXPECTED_EXPORT_PO_FILE = u'''#
msgid ""
msgstr ""

#. Message(s) removed plural
msgctxt "Message(s) removed plural"
msgid "One message removed"
msgstr[0] "One message removed"
msgstr[1] "%d messages deleted"

#. Oceanic
msgctxt "Oceanic"
msgid "Wave"
msgstr "Wave"

msgid "Something to translate"
msgstr "Something to translate"

#. Hand gesture
msgctxt "Hand gesture"
msgid "Wave"
msgstr "Wave"

msgid "Product®™ — Special chars"
msgstr "Product®™ — Special chars"
'''


class POTestCase(TestCase):
    def test_errors_returned(self):
        errors = import_translations_from_po(POFILE, "de", "en")
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0],
            ("Could not find translation: u'something something something something translate', None", "unknown", ""))

    def test_load_str_po(self):
        """Test that a str with multibyte uft-8 chars can parsed correctly"""
        MasterTranslation(text=u"This — that", language_code="en").save()
        MasterTranslation(text=u"something something something something translate", language_code="en").save()

        pofile = """%s

msgid "This — that"
msgstr "Deise — dass"
        """ % POFILE

        errors = import_translations_from_po(pofile, "de", "en")
        self.assertEqual(errors, [])


class ExportPOTestCase(TestCase):
    def test_export(self):
        MasterTranslation(
            text=u"Wave", hint="Hand gesture", language_code="en").save()
        MasterTranslation(
            text=u"Wave", hint="Oceanic", language_code="en").save()
        MasterTranslation(
            text="One message removed",
            hint="Message(s) removed plural",
            plural_text="%d messages deleted",
            language_code="en").save()
        MasterTranslation(
            text=u"Something to translate", language_code="en").save()
        MasterTranslation(
            text=u"Product®™ — Special chars", language_code="en").save()
        po_file = polib.pofile(unicode(
            export_translations_to_po('en').content.decode('utf-8')))
        self.assertEqual(EXPECTED_EXPORT_PO_FILE, po_file.__unicode__())
