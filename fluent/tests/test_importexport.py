# -*- coding: utf-8 -*-
# STANDARD LIB
from StringIO import StringIO

# THIRD PARTY
from djangae.test import TestCase
import polib

# FLUENT
from fluent.importexport import(
    import_translations_from_po,
    export_translations_to_po,
    import_translations_from_arb,
)
from fluent.models import MasterTranslation


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

    def test_export_handles_language_region_codes(self):
        # Fluent should handle 'en-US' as a language code. Previously
        # `export_translations_to_po('en-US')` would raise KeyError.

        MasterTranslation(text=u'Foo', hint=u'Bar', language_code='en').save()

        result = unicode(export_translations_to_po('en-US'))
        expected = (
            u'Content-Type: text/plain\r\n'
            u'Content-Disposition: attachment; filename=django.po\r\n\r\n'
            u'#. Bar\n'
            u'msgctxt "Bar"\n'
            u'msgid "Foo"\n'
            u'msgstr "Foo"\n'
        )

        self.assertEqual(result, expected)


class ImportARBTestCase(TestCase):

    def test_import_translations_from_arb_logs_error_for_invalid_json(self):
        """ If an ARB file with invalid JSON in it is used, that should be logged as an error. """
        input_file = StringIO()
        input_file.write(''' {] ''')  # invalid JSON
        input_file.seek(0)
        errors = import_translations_from_arb(input_file, "fr")
        # We expect there to be one error
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], "Badly formatted ARB file: Expecting property name: line 1 column 3 (char 2)")

    def test_errors_from_utf8_files(self):
        # Fluent should format errors correctly if the err messages reference utf8 strings
        input_file = StringIO()
        input_file.write(u'''{
            "@@locale": "fr",
            "unknown": "Le Chat",
            "@unknown": {
                "context": "",
                "source_text": "ąęźść",
                "type": "text"
            }
        }'''.encode('utf-8'))
        input_file.seek(0)
        errors = import_translations_from_arb(input_file, "fr")
        self.assertEqual(len(errors), 1)
        self.assertTrue(u"ąęźść" in errors[0][0])

    def test_broken_arb_files(self):
        # Fluent should format errors correctly if the err messages reference utf8 strings
        lang = 'en'
        pk1 = MasterTranslation.objects.create(
            language_code=lang,
            text="result",
        ).pk
        input_file = StringIO()
        input_file.write(('''{
            "@@locale": "fr",
            "unknown": "Le Result",
            "@%s": {
                "context": "",
                "source_text": "result",
                "type": "text"
            }
        }''' % pk1).encode('utf-8'))
        input_file.seek(0)
        errors = import_translations_from_arb(input_file, "fr")
        self.assertEqual(len(errors), 1)
        self.assertEqual("Could not find translation for key: @"+pk1, errors[0][0])
