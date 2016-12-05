from djangae.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings

from fluent.models import MasterTranslation, Translation


class MasterTranslationTests(TestCase):
    def test_creation_creates_counterpart(self):
        mt = MasterTranslation.objects.create(
            text="Hello",
            hint="World!",
            language_code="en"
        )

        self.assertEqual(1, Translation.objects.count())
        self.assertTrue("en" in mt.translations_by_language_code)
        self.assertItemsEqual(["en"], mt.translations.values_list("language_code", flat=True))

    def test_adding_new_translations(self):
        mt = MasterTranslation.objects.create(text="Hello World!")
        mt.create_or_update_translation("fr", "Bonjour!")

        self.assertEqual(2, Translation.objects.count())
        self.assertEqual(2, len(mt.translations_by_language_code))
        self.assertItemsEqual(["fr", settings.LANGUAGE_CODE], mt.translations.values_list("language_code", flat=True))

    def test_pk_is_set_correctly(self):
        mt1 = MasterTranslation.objects.create(text="Hello World!", language_code="en")
        self.assertEqual(mt1.pk, MasterTranslation.generate_key("Hello World!", "", "en"))

        mt2 = MasterTranslation.objects.create(text="Hello World!", language_code="fr")
        self.assertEqual(mt2.pk, MasterTranslation.generate_key("Hello World!", "", "fr"))

        # Make sure that it differs
        self.assertNotEqual(mt1.pk, mt2.pk)

    @override_settings(LANGUAGES=[("en", "English"), ("de", "German")])
    def test_text_for_language_code(self):
        mt = MasterTranslation.objects.create(text="Hello World!")
        text = mt.text_for_language_code("de")  # try to fetch an translation we don't have
        self.assertEqual(text, "Hello World!")

        mt.create_or_update_translation("de", "Hallo Welt!")
        text = mt.text_for_language_code("de")
        self.assertEqual(text, "Hallo Welt!")

    def test_unicode_magic_single(self):
        mt = MasterTranslation.objects.create(
            text="Hello",
            hint="World!",
            language_code="en"
        )

        self.assertEqual(unicode(mt), "Hello (en)")

    def test_unicode_magic_plural(self):
        mt = MasterTranslation.objects.create(
            text="Hello",
            plural_text={"h": "Helloes"},
            hint="World!",
            language_code="en"
        )

        self.assertEqual(unicode(mt), "Hello (en plural)")


class TranslationTests(TestCase):
    def test_unicode_magic_single(self):
        mt = MasterTranslation.objects.create(
            text="Hello",
            hint="World!",
            language_code="en"
        )
        translation = Translation.objects.get()

        self.assertEqual(unicode(mt), "Hello (en)")

    def test_unicode_magic_plural(self):
        mt = MasterTranslation.objects.create(
            text="Hello",
            plural_text={"h": "Helloes"},
            hint="World!",
            language_code="en"
        )
        translation = Translation.objects.get()

        self.assertEqual(unicode(mt), "Hello (en plural)")

    def test_clean(self):
        MasterTranslation.objects.create(text="Buttons!")
        translation = Translation.objects.get()
        translation.full_clean()

        translation.plural_texts["o"] = "Buttons%s"
        with self.assertRaises(ValidationError):
            translation.full_clean()

    def test_can_create_translation_from_non_ascii_master(self):
        master_text = u'\u0141uk\u0105\u015b\u017a' # Lukasz.
        mt = MasterTranslation.objects.create(text=master_text)

        # Previously this would raise UnicodeEncodeError.
        mt.create_or_update_translation('en', singular_text=u'Lukasz')
