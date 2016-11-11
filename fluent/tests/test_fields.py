import unittest

from django.db import models
from djangae.test import TestCase

from fluent.fields import (
    TranslatableCharField,
    TranslatableContent,
    find_all_translatable_fields
)
from fluent.models import MasterTranslation
from fluent.patches import monkey_patch

from model_mommy import mommy


class TestModel(models.Model):
    class Meta:
        app_label = "fluent"


    trans = TranslatableCharField(blank=True)
    trans_with_hint = TranslatableCharField(hint="Test", blank=True)
    trans_with_group = TranslatableCharField(group="Test", blank=True)
    trans_with_default = TranslatableCharField(blank=True, default=TranslatableContent(text="Adirondack"))


class TestBadDefaultModel(models.Model):
    class Meta:
        # don't get counted in the locating test
        app_label = "fluent_test"

    trans = TranslatableCharField(default="Not a TranslatableContent object")


class TranslatableCharFieldTests(TestCase):

    def test_unset_translations(self):
        m = TestModel.objects.create()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)
        self.assertEqual("Adirondack", m.trans_with_default.text)

        m.save()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)
        self.assertEqual("Adirondack", m.trans_with_default.text)

        self.assertEqual(m.trans.text_for_language_code("en"), "")
        self.assertEqual(m.trans_with_default.text_for_language_code("en"), "Adirondack")

    def test_setting_and_getting_translation_text(self):
        m = TestModel()
        m.trans.text = "Hello World!"
        m.trans_with_group.text = "Hello World!"
        m.trans_with_hint.text = "Hello World!"
        m.save()

        # get a completely fresh object, no internal caches etc.
        m = TestModel.objects.get()
        text = m.trans.text_for_language_code("en")
        self.assertEqual(text, "Hello World!")

    def test_finding_all_translations_for_a_group(self):
        TestModel.objects.create()
        translations = MasterTranslation.find_by_group("Test")
        self.assertEqual(0, translations.count())

        TestModel.objects.create(trans_with_group=TranslatableContent(text="Hello World!"))

        translations = MasterTranslation.find_by_group("Test")
        self.assertEqual(1, translations.count())

    def test_bad_default_error(self):
        """
        A non-TranslatableContent default value should raise a ValueError
        """
        with self.assertRaises(ValueError):
            TestBadDefaultModel.objects.create()

    def test_with_model_mommy(self):
        monkey_patch()  # Enable custom generator

        obj = mommy.make(TestModel)
        self.assertTrue(obj.trans.text)


class TestLocatingTranslatableFields(TestCase):
    def test_find_all_translatable_fields(self):
        results = find_all_translatable_fields()

        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the 4 fields of TestModel above
        self.assertEqual(4, len(results))
        self.assertEqual(TestModel, results[0][0])
        self.assertEqual(TestModel, results[1][0])
        self.assertEqual(TestModel, results[2][0])
        self.assertEqual(TestModel, results[3][0])

        results = find_all_translatable_fields(with_group="Test")
        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the one field with this group
        self.assertEqual(1, len(results))
        self.assertEqual(TestModel, results[0][0])


class TranslatableContentTestCase(unittest.TestCase):
    def test_repr(self):
        obj = TranslatableContent(text=u'\xc5ukasz') # Lukasz, but with a dirty L.
        result = repr(obj)

        self.assertEqual(result, "<TranslatableContent '\xc3\x85ukasz' lang: en-us>")
        self.assertIsInstance(result, str)

    def test_str(self):
        obj = TranslatableContent(text=u'\xc5ukasz')
        result = str(obj)

        self.assertEqual(result, '\xc3\x85ukasz')
        self.assertIsInstance(result, str)

    def test_unicode(self):
        obj = TranslatableContent(text=u'\xc5ukasz')
        result = unicode(obj)

        self.assertEqual(result, u'\xc5ukasz')
        self.assertIsInstance(result, unicode)
