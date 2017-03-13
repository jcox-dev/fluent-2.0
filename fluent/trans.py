import threading
import logging
import datetime

from django.conf import settings
from django.core.cache import cache


from fluent.cldr.rules import get_plural_index
from fluent.models import Translation

from djangae.db import transaction

logger = logging.getLogger(__file__)


def _language_invalidation_key(language_code):
    return "fluent_{}_invalidated_at".format(language_code)


def _translation_to_dict(trans):
    data = {"singular": trans.text, "plurals": trans.plural_texts}
    data.update(trans.plural_texts)
    return data


class TranslationCache(object):
    def __init__(self):
        self._write_lock = threading.Lock()
        self._translations = {}
        self._translation_load_times = {}
        self._background_threads = {}

    def invalidate(self, language_code=None, globally=True):
        with self._write_lock:
            invalidation_keys = []
            for code in [language_code] if language_code else map(lambda x: x[0], settings.LANGUAGES):
                invalidation_keys.append(_language_invalidation_key(code))

            if language_code and language_code in self._translations:
                del self._translations[language_code]
            elif language_code is None:
                self._translations = {}

            if globally:
                # Set the invalidation keys in memcache to notify all instances to refresh
                now = datetime.datetime.utcnow()
                cache.set_many({k: now for k in invalidation_keys})

    @transaction.non_atomic
    def refetch_language(self, language_code):
        translations = Translation.objects.filter(language_code=language_code)

        new_translations = {}
        for translation in translations:
            key = (translation.denorm_master_text, translation.denorm_master_hint)

            new_translations[key] = _translation_to_dict(translation)

        with self._write_lock:
            self._translations[language_code] = new_translations
            self._translation_load_times[language_code] = datetime.datetime.utcnow()

    def refetch_language_async(self, language_code):
        def run(_this):
            _this.refetch_language(language_code)
            with _this._write_lock:
                del _this._background_threads[language_code]

        with self._write_lock:
            # We already got it!
            if language_code in self._translations:
                return self._translations[language_code]

            # We've already queued a thread for this, so bail
            if language_code in self._background_threads:
                return

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
        # This will trigger off a thread if necessary. If there are valid
        # translations available already for a language they will be returned.
        translations = self.refetch_language_async(language_code)

        if not translations:
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
        connected to the request_finished signal.

        Also invalidates any languages that have been marked as invalid in memcache
    """
    for language_code in TRANSLATION_CACHE._background_threads.keys():
        thread = TRANSLATION_CACHE._background_threads[language_code]
        if thread.is_alive():
            thread.join()


def invalidate_caches_if_necessary(sender, **kwargs):
    """
        Fires at the start of a request, does a single memcache RPC to see if the
        translation caches need invalidating and regenerating
    """

    # Check for any necessary invalidations
    keys = { _language_invalidation_key(x): x for x in map(lambda x: x[0], settings.LANGUAGES) }
    for k, v in cache.get_many(keys.keys()).items():
        # If the time invalidated is greater than the time we loaded, then
        # invalidate the cache for this language
        language_code = keys[k]
        load_time_per_language_code = TRANSLATION_CACHE._translation_load_times.get(language_code)
        if (v and load_time_per_language_code) and v > load_time_per_language_code:
            TRANSLATION_CACHE.invalidate(language_code, globally=False)

            # Start a background thread to regenerate
            TRANSLATION_CACHE.refetch_language_async(language_code)


def translations_loading():
    return bool(TRANSLATION_CACHE._background_threads)


def invalidate_language(language_code):
    TRANSLATION_CACHE.invalidate(language_code)


def _get_trans(text, hint, count=1, language_override=None):
    from django.utils.translation import get_language

    language_code = language_override or get_language()
    # With translations deactivated return the original text
    # Currently this will be the singular form even for pluralized messages
    if language_code is None:
        return unicode(text)

    assert(text is not None)

    # If no text was specified, there won't be a master translation for it
    # so just return the empty text (we check for not
    if not text:
        return u""

    forms = TRANSLATION_CACHE.get_translation(text, hint, language_code)

    if not forms:
        # We have no translation for this text.
        logger.debug(
            "Found string not translated into %s so falling back to default, string was %s",
            language_code, text
        )
        # This unicode() call is important.  If we are here it means that we do not have a
        # translation for this text string, so we want to just return the default text, which is
        # the `text` variable. But if this variable has come from a `{% trans %}` tag, then it will
        # have been through django.template.base.Variable.__init__, which makes the assumption that
        # any string literal defined in a template is safe, and therefore it calls mark_safe() on
        # it.  Fluent's `trans` tag deliberately does NOT make the assumption that string literals
        # defined inside it are safe (because we don't want to send pre-escaped text to translators)
        # and therefore we must remove the assumption that the string is safe. Calling unicode() on
        # it turns it from a SafeText object back to a normal unicode object.
        return unicode(text)

    plural_index = get_plural_index(language_code, count)
    # Fall back to singular form if the correct plural doesn't exist. This will happen until all languages have been re-uploaded.
    if plural_index in forms:
        return forms[plural_index]

    singular_index = get_plural_index(language_code, 1)
    return forms[singular_index]


def gettext(message, group=None):
    return _get_trans(message, hint="").encode("utf-8")


def ugettext(message, group=None):
    from django.utils.encoding import force_unicode
    return force_unicode(_get_trans(message, hint="", count=1))


def pgettext(context, message, group=None):
    return _get_trans(message, hint=context)


def ungettext(singular, plural, number, group=None):
    from django.utils.encoding import force_unicode
    return force_unicode(_get_trans(singular, hint="", count=number))


def ngettext(singular, plural, number, group=None):
    return _get_trans(singular, hint="", count=number).encode("utf-8")


def npgettext(context, singular, plural, number, group=None):
    return _get_trans(singular, context, number)


from django.utils.functional import lazy


gettext_lazy = lazy(gettext, str)
ugettext_lazy = lazy(ugettext, unicode)
pgettext_lazy = lazy(pgettext, unicode)
ngettext_lazy = lazy(ngettext, str)
ungettext_lazy = lazy(ungettext, unicode)
npgettext_lazy = lazy(npgettext, unicode)
