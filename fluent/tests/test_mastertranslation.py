from djangae.test import TestCase

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
