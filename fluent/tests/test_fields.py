from __future__ import unicode_literals
# THIRD PARTY
from builtins import str
from builtins import object
from djangae.contrib import sleuth
from djangae.test import TestCase
from django.db import models
from django.test import override_settings
from django.utils import translation
from model_mommy import mommy

# FLUENT
from fluent.fields import (
    TranslatableCharField,
    TranslatableContent,
    find_all_translatable_fields,
    find_installed_translatable_fields
)
from fluent.models import MasterTranslation
from fluent.patches import monkey_patch


class TranslatedModel(models.Model):
    class Meta(object):
        app_label = "fluent"


    trans = TranslatableCharField(blank=True)
    trans_with_hint = TranslatableCharField(hint="Test", blank=True)
    trans_with_group = TranslatableCharField(group="Test", blank=True)
    trans_with_default = TranslatableCharField(blank=True, default=TranslatableContent(text="Adirondack"))


class BadDefaultModel(models.Model):
    class Meta(object):
        # don't get counted in the locating test
        app_label = "fluent_test"

    trans = TranslatableCharField(default="Not a TranslatableContent object")


class TranslatableCharFieldTests(TestCase):

    def test_unset_translations(self):
        m = TranslatedModel.objects.create()

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
        m = TranslatedModel()
        m.trans.text = "Hello World!"
        m.trans_with_group.text = "Hello World!"
        m.trans_with_hint.text = "Hello World!"
        m.save()

        # get a completely fresh object, no internal caches etc.
        m = TranslatedModel.objects.get()
        text = m.trans.text_for_language_code("en")
        self.assertEqual(text, "Hello World!")

    def test_finding_all_translations_for_a_group(self):
        TranslatedModel.objects.create()
        translations = MasterTranslation.find_by_group("Test")
        self.assertEqual(0, translations.count())

        TranslatedModel.objects.create(trans_with_group=TranslatableContent(text="Hello World!"))

        translations = MasterTranslation.find_by_group("Test")
        self.assertEqual(1, translations.count())

    def test_bad_default_error(self):
        """
        A non-TranslatableContent default value should raise a ValueError
        """
        with self.assertRaises(ValueError):
            BadDefaultModel.objects.create()

    def test_with_model_mommy(self):
        monkey_patch()  # Enable custom generator

        obj = mommy.make(TranslatedModel)
        self.assertTrue(obj.trans.text)

    def test_delete_does_nothing(self):
        """ Test that deleting a MasterTranslation does not delete the model which uses it. """
        TranslatedModel.objects.create(trans=TranslatableContent("whatever"))
        self.assertEqual(TranslatedModel.objects.count(), 1)
        MasterTranslation.objects.all().delete()
        self.assertEqual(TranslatedModel.objects.count(), 1)


class TestLocatingTranslatableFields(TestCase):
    def test_find_all_translatable_fields(self):
        results = find_all_translatable_fields()

        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the 4 fields of TranslatedModel above
        self.assertEqual(4, len(results))
        self.assertEqual(TranslatedModel, results[0][0])
        self.assertEqual(TranslatedModel, results[1][0])
        self.assertEqual(TranslatedModel, results[2][0])
        self.assertEqual(TranslatedModel, results[3][0])

        results = find_all_translatable_fields(with_group="Test")
        # Just filter the results down to this app
        results = [ x for x in results if x[0]._meta.app_label == "fluent" ]

        # Should return the one field with this group
        self.assertEqual(1, len(results))
        self.assertEqual(TranslatedModel, results[0][0])

    def test_find_installed_translatable_fields(self):
        results = find_installed_translatable_fields()

        # Just filter the results down to this app
        fluent_app_translatable_fields = []
        for model in results:
            if model._meta.app_label == 'fluent':
                fluent_app_translatable_fields.extend(results[model])

        # Should return the 4 fields of TranslatedModel above
        self.assertEqual(4, len(fluent_app_translatable_fields))
        self.assertEqual(TranslatedModel, fluent_app_translatable_fields[0].model)
        self.assertEqual(TranslatedModel, fluent_app_translatable_fields[1].model)
        self.assertEqual(TranslatedModel, fluent_app_translatable_fields[2].model)
        self.assertEqual(TranslatedModel, fluent_app_translatable_fields[3].model)

        results = find_installed_translatable_fields(with_groups=["Test"])
        fluent_app_translatable_fields = []
        for model in results:
            if model._meta.app_label == 'fluent':
                fluent_app_translatable_fields.extend(results[model])

        # Should return the one field with this group
        self.assertEqual(1, len(fluent_app_translatable_fields))
        self.assertEqual(TranslatedModel, fluent_app_translatable_fields[0].model)


@override_settings(LANGUAGES=[("en", "English"), ("de", "German")])
class TranslatableContentTestCase(TestCase):

    def tearDown(self):
        super(TranslatableContentTestCase, self).tearDown()
        translation.deactivate()

    def test_repr(self):
        obj = TranslatableContent(text=u'\xc5ukasz')  # Lukasz, but with a dirty L.

        result = repr(obj)
        self.assertEqual(result, "<TranslatableContent '\xc3\x85ukasz' lang: en-us>")
        self.assertIsInstance(result, str)

    def test_repr_with_active_language(self):
        """ repr should give info about the default text, regardless of the active language. """
        obj = TranslatableContent(text=u'\xc5ukasz')  # Lukasz, but with a dirty L.
        translation.activate("de")
        result = repr(obj)
        self.assertEqual(result, "<TranslatableContent '\xc3\x85ukasz' lang: en-us>")

    def test_str(self):
        obj = TranslatableContent(text=u'\xc5ukasz')
        result = str(obj)

        self.assertEqual(result, '\xc3\x85ukasz')
        self.assertIsInstance(result, str)

    def test_str_with_active_language(self):
        """ If there's a currently-active language, str should return the translated text. """

        def mock_get_translation(text, hint, language_code):
            if language_code == "de":
                return {"singular": "translated", "o": "translated"}
            return {"singular": self.text}

        translation.activate("de")
        with sleuth.switch(
            "fluent.fields.trans.TRANSLATION_CACHE.get_translation",
            mock_get_translation
        ):
            obj = TranslatableContent(text=u'\xc5ukasz')
            result = str(obj)

        self.assertEqual(result, 'translated')
        self.assertIsInstance(result, str)

    def test_unicode(self):
        obj = TranslatableContent(text=u'\xc5ukasz')
        result = str(obj)

        self.assertEqual(result, u'\xc5ukasz')
        self.assertIsInstance(result, str)

    def test_unicode_with_active_language(self):
        """ If there's a currently-active language, unicode should return the translated text. """

        def mock_get_translation(text, hint, language_code):
            if language_code == "de":
                return {"singular": "translated", "o": "translated"}
            return {"singular": self.text}

        translation.activate("de")
        with sleuth.switch(
            "fluent.fields.trans.TRANSLATION_CACHE.get_translation",
            mock_get_translation
        ):
            obj = TranslatableContent(text=u'\xc5ukasz')
            result = str(obj)

        self.assertEqual(result, u'translated')
        self.assertIsInstance(result, str)
