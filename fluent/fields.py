from django.db import models

from .models import MasterTranslation


class TranslatableContent(object):
    def __init__(self, master_translation_id=None):
        self._master_translation_id = master_translation_id
        self._cached_master_translation = None

    def _cache_master_translation(self):
        # If we haven't got a cached master translation, look it up
        if not self._cached_master_translation:
            self._cached_master_translation = MasterTranslation.objects.only("text").get(
                pk=self.master_translation_id
            )

    def __unicode__(self):
        # This content hasn't been set yet, so just return nothing
        if not self._master_translation_id:
            return u""

        self._cache_master_translation()

        # Return the master translation text
        return self._cached_master_translation.text

    def text_for_language_code(self, language_code):
        self._cache_master_translation()
        return self._cached_master_translation.text_for_language_code(language_code)


class TranslatableField(models.ForeignKey):
    def __init__(self, *args, **kwargs):
        kwargs["othermodel"] = MasterTranslation # Only FK to MasterTranslation
        kwargs["related_name"] = "+" # Disable reverse relations
        super(TranslatableField, self).__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value

        return TranslatableContent(value)

    def to_python(self, value):
        if isinstance(value, TranslatableContent):
            return value

        if value is None:
            return value

        return TranslatableContent(value)
