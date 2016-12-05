import uuid
from mock import patch, mock_open, Mock

from djangae.contrib import sleuth
from djangae.test import TestCase
from django.template import Template, Context

from fluent.scanner import _scan_list, parse_file, DEFAULT_TRANSLATION_GROUP
from fluent.models import MasterTranslation, ScanMarshall
from fluent.trans import TRANSLATION_CACHE


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
        TRANSLATION_CACHE.invalidate()

    def test_basic_html_parsing(self):
        results = parse_file(TEST_HTML_CONTENT, ".html")
        expected = [
            ('Test trans string with group', '', '', 'public'),
            ('Test trans string without group', '', '', DEFAULT_TRANSLATION_GROUP),
            ('Test & escaping', '', '', DEFAULT_TRANSLATION_GROUP),
            ('Test & unescaping', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest trans block with group\n', '', '', 'public'),
            ('\nTest trans block without group\n', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest blocktrans & escaping\n', '', '', DEFAULT_TRANSLATION_GROUP),
            ('\nTest blocktrans & unescaping\n', '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)

    def test_trans_tag_with_group(self):
        text = "Test trans string with group"
        content = """
{% load fluent %}
{% trans "Test trans string with group" group "public" %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', 'public'),
        ]
        self.assertEqual(results, expected)
        rendered = Template(content).render(Context())
        self.assertTrue("Test trans string with group" in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        mt = MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        mt.used_by_groups_in_code_or_templates = {'public'}
        mt.save()

        rendered = Template(content).render(Context())
        self.assertTrue("Test trans string with group" in rendered)

    def test_trans_tag_without_group(self):
        text = "Test trans string without group"
        content = """
{% load fluent %}
{% trans "Test trans string without group" %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', DEFAULT_TRANSLATION_GROUP)]
        self.assertEqual(results, expected)

        rendered = Template(content).render(Context())
        self.assertTrue(text in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test trans string without group" in rendered)

    def test_trans_tag_and_escaping(self):
        text = "Test & escaping"
        content = """
{% load fluent %}
{% trans "Test & escaping" %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)
        rendered = Template(content).render(Context())
        self.assertTrue("Test &amp; escaping" in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test &amp; escaping" in rendered)

    def test_trans_tag_and_noescape(self):
        text = "Test & unescaping"
        content = """
{% load fluent %}
{% trans "Test & unescaping" noescape %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', DEFAULT_TRANSLATION_GROUP)]
        self.assertEqual(results, expected)

        rendered = Template(content).render(Context())
        self.assertTrue(text in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test & unescaping" in rendered)

    def test_blocktrans_tag_with_group(self):
        text = "\nTest trans block with group\n"
        content = """
{% load fluent %}
{% blocktrans group "public" %}
Test trans block with group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', 'public'),
        ]
        self.assertEqual(results, expected)
        rendered = Template(content).render(Context())
        self.assertTrue(text in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        mt = MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        mt.used_by_groups_in_code_or_templates = {'public'}
        mt.save()

        rendered = Template(content).render(Context())
        self.assertTrue("Test trans block with group" in rendered)

    def test_blocktrans_tag_without_group(self):
        text = "\nTest trans block without group\n"
        content = """
{% load fluent %}
{% blocktrans %}
Test trans block without group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', DEFAULT_TRANSLATION_GROUP)]
        self.assertEqual(results, expected)

        rendered = Template(content).render(Context())
        self.assertTrue(text in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test trans block without group" in rendered)

    def test_blocktrans_tag_and_escaping(self):
        text = "\nTest blocktrans & escaping\n"
        content = """
{% load fluent %}
{% blocktrans %}
Test blocktrans & escaping
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)
        rendered = Template(content).render(Context())
        self.assertTrue("Test blocktrans &amp; escaping" in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test blocktrans &amp; escaping" in rendered)

    def test_blocktrans_tag_and_noescape(self):
        text = "\nTest blocktrans & unescaping\n"
        content = """
{% load fluent %}
{% blocktrans noescape %}
Test blocktrans & unescaping
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', DEFAULT_TRANSLATION_GROUP)]
        self.assertEqual(results, expected)

        rendered = Template(content).render(Context())
        self.assertTrue(text in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context())
        self.assertTrue("Test blocktrans & unescaping" in rendered)

    def test_blocktrans_tag_with_variable_and_group_escaping(self):
        text = '\n<a href="http://google.com">%(name)s</a> in group\n'
        content = """
{% load fluent %}
{% blocktrans group "public" %}
<a href="http://google.com">{{ name }}</a> in group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', 'public'),
        ]
        self.assertEqual(results, expected)

        data = {'name': "Ola & Ola"}
        rendered = Template(content).render(Context(data))
        self.assertTrue('&lt;a href=&quot;http://google.com&quot;&gt;Ola &amp; Ola&lt;/a&gt; in group' in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        mt = MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        mt.used_by_groups_in_code_or_templates = {'public'}
        mt.save()

        rendered = Template(content).render(Context(data))
        self.assertTrue('&lt;a href=&quot;http://google.com&quot;&gt;Ola &amp; Ola&lt;/a&gt; in group' in rendered)

    def test_blocktrans_tag_with_variable_and_with_group_noescaping(self):
        text = '\n<a href="http://google.com">%(name)s</a> in group\n'
        content = """
{% load fluent %}
{% blocktrans noescape group "public" %}
<a href="http://google.com">{{ name }}</a> in group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', 'public')]
        self.assertEqual(results, expected)

        data = {'name': "Ola & Ola"}
        rendered = Template(content).render(Context(data))
        self.assertTrue('<a href="http://google.com">Ola &amp; Ola</a> in group' in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context(data))
        self.assertTrue('<a href="http://google.com">Ola &amp; Ola</a> in group' in rendered)

    def test_blocktrans_tag_with_variable_escaping(self):
        text = '\n<a href="http://google.com">%(name)s</a> without group\n'
        content = """
{% load fluent %}
{% blocktrans %}
<a href="http://google.com">{{ name }}</a> without group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [
            (text, '', '', DEFAULT_TRANSLATION_GROUP),
        ]
        self.assertEqual(results, expected)

        data = {'name': "Ola & Ola"}
        rendered = Template(content).render(Context(data))
        self.assertTrue('&lt;a href=&quot;http://google.com&quot;&gt;Ola &amp; Ola&lt;/a&gt; without group' in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context(data))
        self.assertTrue('&lt;a href=&quot;http://google.com&quot;&gt;Ola &amp; Ola&lt;/a&gt; without group' in rendered)

    def test_blocktrans_tag_with_variable_and_noescaping(self):
        text = '\n<a href="http://google.com">%(name)s</a> without group\n'
        content = """
{% load fluent %}
{% blocktrans noescape %}
<a href="http://google.com">{{ name }}</a> without group
{% endblocktrans %}
        """
        results = parse_file(content, ".html")
        expected = [(text, '', '', DEFAULT_TRANSLATION_GROUP)]
        self.assertEqual(results, expected)

        data = {'name': "Ola & Ola"}
        rendered = Template(content).render(Context(data))
        self.assertTrue('<a href="http://google.com">Ola &amp; Ola</a> without group' in rendered)

        # create master translation for the string and test it renders correctly
        key = MasterTranslation.generate_key(text, '', 'en-us')
        MasterTranslation.objects.create(
            pk=key, text=text, language_code='en-us'
        )
        rendered = Template(content).render(Context(data))
        self.assertTrue('<a href="http://google.com">Ola &amp; Ola</a> without group' in rendered)

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
        rendered = Template(TEST_HTML_CONTENT).render(Context({'name': 'Ola & Ola'}))
        self.assertTrue("Test &amp; escaping" in rendered)
        self.assertTrue("Test & unescaping" in rendered)
        self.assertTrue("Test trans block with group" in rendered)
        self.assertTrue("Test blocktrans &amp; escaping" in rendered)
        self.assertTrue("Test blocktrans & unescaping" in rendered)


class ScanListTest(TestCase):

    def test_scan_list_same_string_in_two_groups(self):
        """Regression test: previously when string was occuring in two or more
        different groups only last one was saved, which is wrong."""

        marshall = ScanMarshall.objects.create()
        with patch('__builtin__.open', mock_open()):
            with sleuth.fake('os.path.exists', return_value=True):
                with sleuth.fake('os.path.splitext', return_value=["some_fake_name", "html"]):
                    with sleuth.fake('fluent.scanner.parse_file', [
                        ("Monday", "", "", "public"),
                        ("Monday", "", "", "website"),
                    ]):
                        _scan_list(marshall, uuid.uuid4(), ['some_fake_name.html'])

        self.assertEquals(MasterTranslation.objects.get().used_by_groups_in_code_or_templates, {"public", "website"})
