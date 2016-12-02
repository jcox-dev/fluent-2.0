import datetime

from djangae.contrib import sleuth

from django.core.cache import cache
from django.utils import translation
from djangae.test import TestCase

from fluent.trans import (
    gettext,
    invalidate_language,
    translations_loading,
    _language_invalidation_key,
    invalidate_caches_if_necessary,
    TRANSLATION_CACHE,
)

from fluent.models import MasterTranslation


class TranslationTests(TestCase):

    def setUp(self):
        TRANSLATION_CACHE.invalidate()
        self.mt = MasterTranslation.objects.create(
            text="Hello World!",
            language_code="en"
        )
        self.mt.create_or_update_translation("de", u"Hallo Welt!")
        self.mt.create_or_update_translation("es", u"Hola Mundo!")

        self.mt2 = MasterTranslation.objects.create(
            text="Goodbye World!",
            language_code="en"
        )
        self.mt2.create_or_update_translation("de", u"Auf Wiedersehen Welt!")

        invalidate_language("en")
        invalidate_language("de")
        invalidate_language("es")

    def tearDown(self):
        translation.deactivate()

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

    def test_languages_cached(self):
        # This should make a query, because the translations were invalidated
        translation.activate("de")
        with sleuth.watch("google.appengine.api.datastore.Query.Run") as query:
            trans = gettext("Hello World!")
            self.assertEqual(trans, "Hallo Welt!")
            self.assertTrue(query.called)

        # Wait for any background threads to finish
        while translations_loading():
            pass

        # This shouldn't make a query
        with sleuth.watch("google.appengine.api.datastore.Query.Run") as query:
            trans = gettext("Goodbye World!")
            self.assertEqual(trans, "Auf Wiedersehen Welt!")
            self.assertFalse(query.called)

    def test_memcache_invalidates_when_the_request_ends(self):
        translation.activate("de")
        gettext("Hello World!") # Generates the cache

        # Wait for any background threads to finish
        while translations_loading():
            pass

        # Set the invalidation key
        key = _language_invalidation_key("de")
        cache.set(key, datetime.datetime.utcnow())

        # This shouldn't make a query, the invalidation hasn't applied yet
        with sleuth.watch("google.appengine.api.datastore.Query.Run") as query:
            trans = gettext("Goodbye World!")
            self.assertEqual(trans, "Auf Wiedersehen Welt!")
            self.assertFalse(query.called)

        # Run the finished signal
        invalidate_caches_if_necessary(None)

        # This should now cause a query
        with sleuth.watch("google.appengine.api.datastore.Query.Run") as query:
            trans = gettext("Goodbye World!")
            self.assertEqual(trans, "Auf Wiedersehen Welt!")
            self.assertTrue(query.called)
