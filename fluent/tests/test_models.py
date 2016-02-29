from djangae.test import TestCase
from django.conf import settings
from django.core.exceptions import ValidationError

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

    def test_text_for_language_code(self):
        mt = MasterTranslation.objects.create(text="Hello World!")
        text = mt.text_for_language_code("de")  # try to fetch an translation we don't have
        self.assertEqual(text, "Hello World!")

        mt.create_or_update_translation("de", "Hallo Welt!")
        text = mt.text_for_language_code("de")
        self.assertEqual(text, "Hallo Welt!")


class TranslationTests(TestCase):
    def test_clean(self):
        MasterTranslation.objects.create(text="Buttons!")
        translation = Translation.objects.get()
        translation.full_clean()

        translation.plural_texts["o"] = "Buttons%s"
        with self.assertRaises(ValidationError):
            translation.full_clean()
