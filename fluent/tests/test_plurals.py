# -*- coding: utf-8 -*-
#SYSTEM
import re
import json
from StringIO import StringIO
import os.path
import xml.etree.ElementTree as ET

#LIBRARIES
from django.conf import settings
from django.test import TestCase
from django.utils import translation


#FLUENT
from fluent.models import MasterTranslation, Translation
from fluent import cldr
from fluent.trans import ngettext, gettext, invalidate_language
from fluent.cldr.rules import get_plural_index  # dummy implementation just for tests
from fluent.importexport import import_translations_from_arb, import_translations_from_po
from fluent.cldr import expr_parser


class TestPluralRules(TestCase):
    @classmethod
    def setUpClass(cls):
        test_fixture = os.path.join(os.path.dirname(__file__), 'plurals.xml')
        tree = ET.parse(test_fixture)
        root = tree.getroot()

        #lang_dict = getattr(settings, "ALTERNATIVES_DICT", dict((x, x) for x, y in settings.LANGUAGES))
        # we don't have rules for those languages
        SUPPORTED_LANGUAGES = cldr.LANGUAGE_LOOKUPS.keys()

        # Parse the xml and come up with a dict of example values:
        cls.examples = []
        for ruleset in root.iter('pluralRules'):
            locales = [l.split('_')[0] for l in ruleset.attrib['locales'].split()]
            locales = [l for l in locales if l in SUPPORTED_LANGUAGES]
            if not locales:
                continue
            data = {'locales': locales}
            for rule in ruleset:
                example_values = []
                example_sets = rule.text.split('@')[1:]
                if not example_sets:
                    continue

                for example_set in example_sets:
                    if example_set.startswith('integer'):
                        t = int
                    elif example_set.startswith('decimal'):
                        t = float
                    else:
                        raise ValueError('Bad example data: '+rule.text)

                if t is int:
                    for range_text in re.findall(r'([0-9]+~[0-9]+)', example_set):
                        r_start, r_end = map(int, range_text.split('~'))
                        example_values.extend(range(r_start, r_end))

                values_list = re.sub(u'~|,|…', ' ', example_set).split()[1:]
                example_values.extend(map(t, values_list))
                data[cldr.ICU_KEYWORDS[rule.attrib['count']]] = set(example_values)
            cls.examples.append(data)

    def test_plural_rules(self):
        """ Test all example values from plurals.xml against our pluralization rules."""
        for example in self.examples:
            for locale in example['locales']:
                for keyword, values in example.items():
                    if keyword == 'locales':
                        continue

                    for v in values:
                        computed = get_plural_index(locale, v)
                        self.assertEqual(keyword, computed, "For language %s (%s) value: %r, expected: %s, got: %s" % (locale, ', '.join(example['locales']), v, keyword, computed))

    def test_pl_arb_manually(self):
        lang = settings.LANGUAGE_CODE
        invalidate_language("pl")
        self.assertEqual(Translation.objects.count(), 0)
        pk1 = MasterTranslation.objects.create(
            language_code=lang,
            text="result",
            plural_text="results",
        ).pk
        pk2 = MasterTranslation.objects.create(
            language_code=lang,
            text="cat",
        ).pk
        data = {
            "@@locale": "pl",
            # two form isn't needed or used by the pl lookup function so it should be ignored
            pk1: u"{NUM, plural, one {wynik} few {wyniki} two {blabla} many {wyników} other {wyniku}}",
            "@"+pk1: {
                "context": "",
                "source_text": "result",
                "type": "text"
            },
            pk2: u"kot",
            "@"+pk2: {
                "context": "",
                "source_text": "cat",
                "type": "text"
            },
        }
        mock_file = StringIO(json.dumps(data))
        import_translations_from_arb(mock_file, "pl")

        translation.activate("pl")
        self.assertEqual(ngettext("result", "", 0).decode('utf-8'), u"wyników")
        self.assertEqual(ngettext("result", "", 1).decode('utf-8'), u"wynik")
        self.assertEqual(ngettext("result", "", 2).decode('utf-8'), u"wyniki")
        self.assertEqual(ngettext("result", "", 5).decode('utf-8'), u"wyników")
        self.assertEqual(ngettext("result", "", 0.5).decode('utf-8'), u"wyniku")

        # Singlar translation test
        self.assertEqual(gettext("cat"), u"kot")

        self.assertEqual(get_plural_index("pl", 0), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1), cldr.ONE)
        self.assertEqual(get_plural_index("pl", 2), cldr.FEW)
        self.assertEqual(get_plural_index("pl", 5), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1.1), cldr.OTHER)

    def test_pl_po_manually(self):
        lang = settings.LANGUAGE_CODE
        invalidate_language("pl")
        self.assertEqual(Translation.objects.count(), 0)
        MasterTranslation.objects.create(
            language_code=lang,
            text="%(n)s result",
            plural_text="%(n)s results",
        )
        MasterTranslation.objects.create(
            language_code=lang,
            text="cat",
        )
        mock_file_contents = u'''# Something something
# Translators list
msgid ""
msgstr ""
"Project-Id-Version: django\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2015-01-17 11:07+0100\n"
"PO-Revision-Date: 2015-01-18 15:19+0000\n"
"Last-Translator: Janusz Harkot <jh@blueice.pl>\n"
"Language-Team: Polish (http://www.transifex.com/projects/p/django/language/"
"pl/)\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Language: pl\n"
"Plural-Forms: nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 "
"|| n%100>=20) ? 1 : 2);\n"

#, python-format
msgid "%(n)s result"
msgid_plural "%(n)s results"
msgstr[0] "%(n)s wynik"
msgstr[1] "%(n)s wyniki"
msgstr[2] "%(n)s wyników"

#, python-format
msgid "cat"
msgstr "kot"
'''
        #msgctxt "context hint"
        import_translations_from_po(mock_file_contents, "pl", lang)
        translation.activate("pl")
        self.assertEqual(ngettext("%(n)s result", "", 0).decode('utf-8'), u"%(n)s wyników")
        self.assertEqual(ngettext("%(n)s result", "", 1).decode('utf-8'), u"%(n)s wynik")
        self.assertEqual(ngettext("%(n)s result", "", 2).decode('utf-8'), u"%(n)s wyniki")
        self.assertEqual(ngettext("%(n)s result", "", 5).decode('utf-8'), u"%(n)s wyników")

        # Singlar translation test
        self.assertEqual(gettext("cat"), u"kot")
        # This form is wrong because po don't support the fraction plural form!
        self.assertEqual(ngettext("%(n)s result", "", 0.5).decode('utf-8'), u"%(n)s wyników")  # u")

        self.assertEqual(get_plural_index("pl", 0), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1), cldr.ONE)
        self.assertEqual(get_plural_index("pl", 2), cldr.FEW)
        self.assertEqual(get_plural_index("pl", 5), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1.1), cldr.OTHER)

    def test_po_plural_forms(self):
        po_plural_form = '(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2)'
        po_python_expr =  lambda n: 0 if n == 1 else 1 if (n % 10 >= 2 and n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20)) else 2

        expr = expr_parser.parse(po_plural_form)
        for i in range(200):
            self.assertEqual(expr_parser.calculate(expr, i), po_python_expr(i))

