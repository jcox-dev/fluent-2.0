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
from fluent.models import MasterTranslation
from fluent import cldr
from fluent.trans import ngettext
from fluent.cldr_rules import get_plural_index  # dummy implementation just for tests
from fluent.importexport import import_translations_from_arb


class TestPluralRules(TestCase):
    @classmethod
    def setUpClass(cls):
        test_fixture = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plurals.xml')
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

    def test_pl_manually(self):
        lang = settings.LANGUAGE_CODE
        pk = MasterTranslation.objects.create(
            id=100,
            language_code=lang,
            text="horse",
            plural_text="horses",
        ).pk
        data = {
            "@@locale": "pl",
            # Excessive 'two' keyword to make the old import work
            pk: u"{NUM, plural, one {koń} few {konie} two {konie} many {koni} other {konia}}",
            "@"+pk: {
                "context": "",
                "source_text": "horse",
                "type": "text"
            }
        }
        mock_file = StringIO(json.dumps(data))
        import_translations_from_arb(mock_file, "pl")
        translation.activate("pl")

        self.assertEqual(ngettext("horse", "", 0).decode('utf-8'), u"koni")
        self.assertEqual(ngettext("horse", "", 1).decode('utf-8'), u"koń")
        self.assertEqual(ngettext("horse", "", 2).decode('utf-8'), u"konie")
        self.assertEqual(ngettext("horse", "", 5).decode('utf-8'), u"koni")
        self.assertEqual(ngettext("horse", "", 1.5).decode('utf-8'), u"konia")

        self.assertEqual(get_plural_index("pl", 0), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1), cldr.ONE)
        self.assertEqual(get_plural_index("pl", 2), cldr.FEW)
        self.assertEqual(get_plural_index("pl", 5), cldr.MANY)
        self.assertEqual(get_plural_index("pl", 1.1), cldr.OTHER)
