from __future__ import unicode_literals
# THIRD PARTY
from djangae.test import TestCase
from django.test import override_settings

# FLUENT
from fluent.utils import find_closest_supported_language


class UtilsTestCase(TestCase):

    def test_find_closest_supported_language(self):
        """ Test the `find_closest_supported_language` function. """
        # If the language code matches exactly, then it should just be returned
        with override_settings(LANGUAGES=[('en', 'English')]):
            self.assertEqual(find_closest_supported_language("en"), "en")

        # Same exact matching logic applies to 2-part language codes
        with override_settings(LANGUAGES=[('en-us', 'English')]):
            self.assertEqual(find_closest_supported_language("en-us"), "en-us")

        # If the language code is in 2 parts and the first half matches one of the supported
        # languages then it should return that supported language
        with override_settings(LANGUAGES=[('en', 'English')]):
            self.assertEqual(find_closest_supported_language("en-us"), "en")

        # If the language code matches the first half of one of the supported languages then it
        # should return that supported language
        with override_settings(LANGUAGES=[('en-us', 'English')]):
            self.assertEqual(find_closest_supported_language("en"), "en-us")

        # If there is no sensible match then it should raise ValueError
        with override_settings(LANGUAGES=[('fr', 'Francais')]):
            self.assertRaises(ValueError, find_closest_supported_language, "en")
