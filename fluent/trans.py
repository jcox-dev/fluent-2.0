import threading
import logging

from django.conf import settings

from fluent import cldr_rules
from djangae.db import transaction

from google.appengine.ext.deferred import defer


_state = threading.local()

LANGUAGE_TRANSLATIONS_KEY = "fluent_translations_%s"


def invalidate_language(language_code):
    from django.core.cache import cache
    if hasattr(_state, "translations_dicts") and language_code in _state.translations_dicts:
        del _state.translations_dicts
    cache.delete(LANGUAGE_TRANSLATIONS_KEY % language_code)

def _translation_to_dict(trans):
    data = {"singular": trans.text, "plurals": trans.plural_texts}
    data.update(trans.plural_texts)
    return data

def _load_into_memcache(language_code):
    from django.core.cache import cache
    from .models import Translation

    logging.info("Reloading translations from the database for %s", language_code)
    # Not in cache or local state, so let's query...
    with transaction.non_atomic():
        translations = Translation.objects.filter(language_code=language_code)

    translations_dict = {}
    for t in translations:
        translations_dict[(t.denorm_master_text, t.denorm_master_hint)] = _translation_to_dict(t)

    if not getattr(_state, "translations_dict", None):
        _state.translations_dicts = {}

    _state.translations_dicts[language_code] = translations_dict

    cache.set(LANGUAGE_TRANSLATIONS_KEY % language_code, translations_dict)
    return translations_dict

def _get_translations_dict(language_code, text=None, hint=None):
    """ Returns a dict of all the translations for the given language_code,
        where the key is a tuple of (default, hint) and the value is
        the translated text.
        Tries to get it in this order:
        1. From thread locals
        2. From memcache
        3. From the database.
        Note that it is quicker to fetch all the translations for a language
        in a single query and store them in a dict than it is to do a separate
        query for each translation, hence this approach.

        If you specify text, and hint, the update will be done offline and the result
        of this function will just be a dictionary containing the single translation you
        were after
    """
    from django.core.cache import cache
    from .models import Translation, MasterTranslation

    if not getattr(_state, 'translations_dicts', None):
        _state.translations_dicts = {}

    try:
        return _state.translations_dicts[language_code]
    except KeyError:
        pass

    # Getting from local state failed so lets try memcache
    cached = cache.get(LANGUAGE_TRANSLATIONS_KEY % language_code)
    if cached:
        # Add to the local state, and then return it
        _state.translations_dicts[language_code] = cached
        return cached

    # If we specified the text and hint we were looking for, we defer the cache update
    # and then return that specific translation. Otherwise we do the update inline and
    # return the entire dictionary. Note we only defer the update if the translation was
    # in the database. This is because the language code might not exist, so we'd continually
    # defer tasks for that language
    if text:
        try:
            # we use settings.LANGUAGE_CODE because this should only ever be called for translations
            # in templates or code which always have a master language of settings.LANGUAGE_CODE unlike
            # translatablefields which may have different, but then they have access to the master language
            # code directly. If this assumption is somehow wrong I'm not sure what else to do here...
            master_key = MasterTranslation.generate_key(text, hint, settings.LANGUAGE_CODE)
            with transaction.non_atomic():
                t = Translation.objects.get(language_code=language_code, master_translation_id=master_key)
            ret = { (text, hint): _translation_to_dict(t) }
        except Translation.DoesNotExist:
            ret = {}

        if ret:
            defer(_load_into_memcache, language_code) #Populate the cache offline

        return ret
    else:
        return _load_into_memcache(language_code)


def _get_trans(text, hint, count=1, language_override=None):
    fluent_disabled = getattr(_state, "fluent_disabled", False)
    if fluent_disabled:
        return text

    from django.utils.translation import get_language

    language_code = language_override or get_language()

    translations_dict = _get_translations_dict(language_code, text, hint)
    try:
        # New rules - everything including the singular translation is in a single dict
        forms = translations_dict[(text, hint)]

        plural_index = cldr_rules.get_plural_index(language_code, count)
        # Fall back to singular form if the correct plural doesn't exist. This will happen until all languages have been re-uploaded.
        if plural_index in forms:
            return forms[plural_index]

        singular_index = cldr_rules.get_plural_index(language_code, 1)
        return forms[singular_index]

    except KeyError:
        # Don't log anything for the default language, translations are only needed for plural forms there.
        if language_code != settings.LANGUAGE_CODE:
            logging.info("Found string not translated into %s so falling back to default, string was %s", language_code, text)
        return text


def gettext(message):
    return _get_trans(message, hint="").encode("utf-8")


def ugettext(message):
    from django.utils.encoding import force_unicode
    return force_unicode(_get_trans(message, hint="", count=1))


def pgettext(context, message):
    return _get_trans(message, hint=context)


def ungettext(singular, plural, number):
    from django.utils.encoding import force_unicode
    return force_unicode(_get_trans(singular, hint="", count=number))


def ngettext(singular, plural, number):
    return _get_trans(singular, hint="", count=number).encode("utf-8")


def npgettext(context, singular, plural, number):
    return _get_trans(singular, context, number)

from django.utils.functional import lazy

gettext_lazy = lazy(gettext, str)
ugettext_lazy = lazy(ugettext, unicode)
pgettext_lazy = lazy(pgettext, unicode)
ngettext_lazy = lazy(ngettext, str)
ungettext_lazy = lazy(ungettext, unicode)
npgettext_lazy = lazy(npgettext, unicode)
