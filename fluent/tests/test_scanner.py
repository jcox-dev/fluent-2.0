from djangae.test import TestCase

from fluent.scanner import parse_file, DEFAULT_TRANSLATION_GROUP


TEST_HTML_CONTENT = """{% trans "Test trans string with group" group "public" %}
{% trans "Test trans string without group" %}
Regular string
{% blocktrans group "public" %}
Test trans block with group
{% endblocktrans %}
{% blocktrans %}
Test trans block without group
{% endblocktrans %}"""

TEST_PYTHON_CONTENT = """_('Test string')
_('Test string with hint', 'hint')
_('Test string with group', group='public')
_('Test string with hint and group', 'hint', group='public')
_('Plural string with hint and group', 'plural', 2, 'hint', group='public')"""

class ScannerTests(TestCase):

    def setUp(self):
        pass

    def test_basic_html_parsing(self):
        results = parse_file(TEST_HTML_CONTENT, ".html")
        expected = [
            ('Test trans string with group', '', '', 'public'),
            ('Test trans string without group', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest trans block with group\n', '', '', 'public'),
            ('\nTest trans block without group\n', '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)

    def test_basic_python_parsing(self):
        results = parse_file(TEST_PYTHON_CONTENT, ".py")
        expected = [
            ('Test string', '', '', DEFAULT_TRANSLATION_GROUP),
            ('Test string with hint', '', 'hint', DEFAULT_TRANSLATION_GROUP),
            ('Test string with group', '', '', 'public'),
            ('Test string with hint and group', '', 'hint', 'public'),
            ('Plural string with hint and group', 'plural', 'hint', 'public'),
        ]
        self.assertEqual(results, expected)
