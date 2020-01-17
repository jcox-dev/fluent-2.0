from __future__ import unicode_literals
import unittest

from fluent.cldr import rules


class GetRulesForLanguageTestCase(unittest.TestCase):
    def test_returns_plural_function_for_language_code(self):
        result = rules.get_rules_for_language('en')

        self.assertIn('en', rules.LANGUAGE_LOOKUPS)
        self.assertEqual(result, rules.l_one_or_many_or_fraction)

    def test_returns_default_for_unknown_language_code(self):
        result = rules.get_rules_for_language('foo')

        self.assertNotIn('foo', rules.LANGUAGE_LOOKUPS)
        self.assertEqual(result, rules._default)

    def test_handles_language_code_with_region(self):
        result = rules.get_rules_for_language('en-us')

        self.assertNotIn('en-us', rules.LANGUAGE_LOOKUPS)
        self.assertEqual(result, rules.l_one_or_many_or_fraction)

    def test_handles_upper_case_language_code(self):
        result = rules.get_rules_for_language('EN')

        self.assertNotIn('EN', rules.LANGUAGE_LOOKUPS)
        self.assertEqual(result, rules.l_one_or_many_or_fraction)
