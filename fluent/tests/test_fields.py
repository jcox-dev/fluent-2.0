
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


class TranslatableCharFieldTests(TestCase):

    def test_unset_translations(self):
        m = TestModel.objects.create()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)

        m.save()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)

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

    def test_with_model_mommy(self):
        monkey_patch()  # Enable custom generator

        obj = mommy.make(TestModel)
        self.assertTrue(obj.trans.text)


class TestLocatingTranslatableFields(TestCase):
    def test_find_all_translatable_fields(self):
        results = find_all_translatable_fields()

        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the 3 fields of TestModel above
        self.assertEqual(3, len(results))
        self.assertEqual(TestModel, results[0][0])
        self.assertEqual(TestModel, results[1][0])
        self.assertEqual(TestModel, results[2][0])

        results = find_all_translatable_fields(with_group="Test")
        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the one field with this group
        self.assertEqual(1, len(results))
        self.assertEqual(TestModel, results[0][0])
