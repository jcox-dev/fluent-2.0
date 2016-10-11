from djangae.test import TestCase
from django.template import Template, Context

from fluent.scanner import parse_file, DEFAULT_TRANSLATION_GROUP


TEST_HTML_CONTENT = """{% load fluent %}
{% trans "Test trans string with group" group "public" %}
{% trans "Test trans string without group" %}
{% trans "Test & escaping" %}
{% trans "Test & unescaping" noescape %}
Regular string
{% blocktrans group "public" %}
Test trans block with group
{% endblocktrans %}
{% blocktrans %}
Test trans block without group
{% endblocktrans %}
{% blocktrans %}
Test blocktrans & escaping
{% endblocktrans %}
{% blocktrans noescape %}
Test blocktrans & unescaping
{% endblocktrans %}
"""

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
            ('Test & escaping', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest trans block with group\n', '', '', 'public'),
            ('\nTest trans block without group\n', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest blocktrans & escaping\n', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest blocktrans & unescaping\n', '', '', DEFAULT_TRANSLATION_GROUP),
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

    def test_render_and_escaping(self):
        rendered = Template(TEST_HTML_CONTENT).render(Context({}))
        self.assertTrue("Test &amp; escaping" in rendered)
        self.assertTrue("Test & unescaping" in rendered)
        self.assertTrue("Test trans block with group" in rendered)
        self.assertTrue("Test blocktrans &amp; escaping" in rendered)
        self.assertTrue("Test blocktrans & unescaping" in rendered)
