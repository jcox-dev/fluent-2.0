from django.utils import translation
from djangae.test import TestCase

from fluent.trans import (
    gettext
)

from fluent.models import MasterTranslation

class TranslationTests(TestCase):

    def setUp(self):
        self.mt = MasterTranslation.objects.create(
            text="Hello World!",
            language_code="en"
        )
        self.mt.create_or_update_translation("de", "Hallo Welt!")
        self.mt.create_or_update_translation("es", "Hola Mundo!")

    def test_gettext(self):
        translation.activate("es")
        trans = gettext("Hello World!")
        self.assertEqual(trans, "Hola Mundo!")

        translation.activate("de")
        trans = gettext("Hello World!")
        self.assertEqual(trans, "Hallo Welt!")

        translation.activate("en")
        trans = gettext("Hello World!")
        self.assertEqual(trans, "Hello World!")

        # Untranslated
        translation.activate("fr")
        trans = gettext("Hello World!")
        self.assertEqual(trans, "Hello World!")
