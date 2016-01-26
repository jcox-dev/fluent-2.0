from django.conf import settings
from django.db import models

from .models import MasterTranslation


class TranslatableContent(object):
    def __init__(self, default_hint, master_translation_id=None):
        self._master_translation_id = master_translation_id
        self._master_translation_cache = None
        self._text = u""
        self._hint = default_hint
        self._language_code = None if master_translation_id else settings.LANGUAGE_CODE

    def _load_master_translation(self):
        if self._master_translation_id and not self._master_translation_cache:
            self._master_translation_cache = MasterTranslation.objects.get(
                pk=self._master_translation_id
            )

            self._text = self.master_translation_cache_.text
            self._hint = self.master_translation_cache_.hint
            self._language_code = self.master_translation_cache_.language_code


    @property
    def text(self):
        self._load_master_translation()
        return self._text

    @text.setter
    def text(self, value):
        self._text = value

    @property
    def language_code(self):
        self._load_master_translation()
        return self._language_code

    @language_code.setter
    def language_code(self, language_code):
        self._language_code = language_code

    @property
    def hint(self):
        self._load_master_translation()
        return self._hint

    @hint.setter
    def hint(self, value):
        self._hint = value

    def _cache_master_translation(self):
        # If we haven't got a cached master translation, look it up
        if not self._cached_master_translation:
            self._cached_master_translation = MasterTranslation.objects.only("text").get(
                pk=self.master_translation_id
            )

    def __unicode__(self):
        self._load_master_translation()
        return self.text

    def __repr__(self):
        return u"<TranslatableContent '{}' lang: {}>".format(self.text, self.language_code)

    def text_for_language_code(self, language_code):
        self._cache_master_translation()
        return self._cached_master_translation.text_for_language_code(language_code)

    def save(self):
        return MasterTranslation.objects.get_or_create(
            pk=MasterTranslation.generate_key(self.text, self.hint, self.language_code),
            defaults={
                "text": self.text,
                "hint": self.hint,
                "language_code": self.language_code
            }
        )[0]


class TranslatableFieldDescriptor(object):
    def __get__(self, instance, instance_type):
        pass

    def __set__(self, instance, value):
        pass



class TranslatableField(models.ForeignKey):
    def __init__(self, hint=u"", group=None, *args, **kwargs):
        self.hint = hint
        self.group = group

        kwargs["related_name"] = "+" # Disable reverse relations
        kwargs["null"] = True

        # Only FK to MasterTranslation
        super(TranslatableField, self).__init__(MasterTranslation, *args, **kwargs)

    def pre_save(self, model_instance, add):
        content = getattr(model_instance, self.attname)
        setattr(
            model_instance,
            self.column,
            content.save().pk
        )

        super(TranslatableField, self).pre_save(model_instance, add)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return TranslatableContent(default_hint=self.hint)

        return TranslatableContent(default_hint=self.hint, master_translation_id=value)

    def to_python(self, value):
        if isinstance(value, TranslatableContent):
            return value

        if value is None:
            return TranslatableContent(default_hint=self.hint)

        return TranslatableContent(default_hint=self.hint, master_translation_id=value)
