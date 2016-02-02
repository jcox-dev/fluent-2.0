import threading
import logging

from django.conf import settings

from fluent import cldr_rules
from fluent.models import Translation

from djangae.db import transaction

from google.appengine.ext.deferred import defer

logger = logging.getLogger(__file__)

def _translation_to_dict(trans):
    data = {"singular": trans.text, "plurals": trans.plural_texts}
    data.update(trans.plural_texts)
    return data

class TranslationCache(object):
    def __init__(self):
        self._write_lock = threading.Lock()
        self._translations = {}
        self._background_threads = {}

    def invalidate(self, language_code=None):
        with self._write_lock:
            if language_code and language_code in self._translations:
                del self._translations[language_code]
            elif language_code is None:
                self._translations = {}

    @transaction.non_atomic
    def refetch_language(self, language_code):
        translations = Translation.objects.filter(language_code=language_code)

        new_translations = {}
        for translation in translations:
            key = (translation.denorm_master_text, translation.denorm_master_hint)

            new_translations[key] = _translation_to_dict(translation)

        with self._write_lock:
            self._translations[language_code] = new_translations

    def refetch_language_async(self, language_code):
        if language_code in self._background_threads:
            return # We're already doing stuff!

        def run(_this):
            _this.refetch_language(language_code)
            del _this._background_threads[language_code]

        self._background_threads[language_code] = threading.Thread(
            target=run,
            args=(self,)
        )
        self._background_threads[language_code].start()

    @transaction.non_atomic
    def fetch_translation(self, text, hint, language_code):
        return Translation.objects.filter(
            master_text_hint_hash=Translation.generate_hash(text, hint),
            language_code=language_code
        ).first()

    def get_translation(self, text, hint, language_code):
        if language_code not in self._translations:
            # We need to grab the entire language's translation's so we
            # defer a task to do that targetting this specific instance
            self.refetch_language_async(language_code)

            translation = self.fetch_translation(text, hint, language_code)
            if translation:
                return _translation_to_dict(translation)
        else:
            return self._translations[language_code].get(
                (text, hint)
            )


# Global variable so that we only need to fetch stuff once per
# instance
TRANSLATION_CACHE = TranslationCache()

def ensure_threads_join(sender, **kwargs):
    """ Makes sure any background threads complete. Is
        connected to the request_finished signal
    """
    for language_code in TRANSLATION_CACHE._background_threads.keys():
        thread = TRANSLATION_CACHE._background_threads[language_code]
        if thread.is_alive():
            thread.join()


def invalidate_language(language_code):
    TRANSLATION_CACHE.invalidate(language_code)


def _get_trans(text, hint, count=1, language_override=None):
    from django.utils.translation import get_language

    language_code = language_override or get_language()

    forms = TRANSLATION_CACHE.get_translation(text, hint, language_code)

    if not forms:
        logger.debug("Found string not translated into %s so falling back to default, string was %s", language_code, text)
        return text

    plural_index = cldr_rules.get_plural_index(language_code, count)
    # Fall back to singular form if the correct plural doesn't exist. This will happen until all languages have been re-uploaded.
    if plural_index in forms:
        return forms[plural_index]

    singular_index = cldr_rules.get_plural_index(language_code, 1)
    return forms[singular_index]


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
