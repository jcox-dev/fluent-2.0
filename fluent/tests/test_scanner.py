from djangae.test import TestCase

from fluent.scanner import parse_file, DEFAULT_TRANSLATION_GROUP


TEST_CONTENT = """{% trans "Test trans string with group" group "public" %}
{% trans "Test trans string without group" %}
Regular string
{% blocktrans group "public" %}
Test trans block with group
{% endblocktrans %}
{% blocktrans %}
Test trans block without group
{% endblocktrans %}"""


class ScannerTests(TestCase):

    def setUp(self):
        pass

    def test_basic_html_parsing(self):
        results = parse_file(TEST_CONTENT, ".html")
        expected = [
            ('Test trans string with group', '', '', 'public'),
            ('Test trans string without group', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest trans block with group\n', '', '', 'public'),
            ('\nTest trans block without group\n', '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)
