from __future__ import unicode_literals
from builtins import next
from django.conf import settings


def find_closest_supported_language(language_code):
    lookup = list(dict(settings.LANGUAGES).keys())

    # If it's in there, return this supported language
    if language_code in lookup:
        return language_code

    # If this is a dialect, then see if the root language is there
    root_language = language_code.split("-")[0]
    if root_language in lookup:
        return root_language

    try:
        # Finally, if there is another dialect with the same root language
        # then return that, otherwise raise an error
        check = "{}-".format(root_language)
        return next((x for x in lookup if x.startswith(check)))
    except StopIteration:
        raise ValueError(
            "Unable to find a suitable match for language_code: {}".format(language_code)
        )
