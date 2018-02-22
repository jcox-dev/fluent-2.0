# -*- coding: utf8 -*-
from django.conf import settings
from django.db import models
from django.db import IntegrityError
from django.core.exceptions import FieldDoesNotExist
from django.utils.translation import get_language
from django import forms

from djangae.utils import deprecated
from djangae.fields import JSONField

from .models import MasterTranslation
from . import trans


# A name for the JSONField to store MasterTranslations data. A model with at least one
# TranslatableCharField will get a JSONField to cache the text
# given model.
MASTERS_CACHE_ATTR = '_fluent_cache'


class TranslatableContent(object):
    """ Object which represents a piece of translatable content, including its hint, original
        language code and ID of the corresponding MasterTranslation ID.
        Renders itself as the translated string (for the currently active language) when cast
        to unicode or string (similar to ugettext_lazy).

        This is the object which is set as the value of the attribute on a model when a
        TranslatableCharField is used.  E.g. if your model has:
        `title = TranslatableCharField()`
        then an instance of that model will have a TranslatableContent() instance as the value of
        the `title` attribute.
    """

    # Django 1.8.4 and later check related fields have saved objects assigned
    # to them *before* pre_save is called. This means our neat little trick of
    # returning a MasterTranslation on pre_save will fail. So we'll set pk = 0,
    # as 0 is an invalid ID for the datastore
    pk = 0

    def __init__(self, text=u"", hint=u"", language_code=None, master_translation_id=None):
        if text or hint:
            master_translation_id = None

        self._master_translation_id = master_translation_id
        self._master_translation_cache = None
        self._text = text
        self._hint = hint
        self._language_code = None if master_translation_id else (language_code or settings.LANGUAGE_CODE)

    @property
    def is_effectively_null(self):
        return (not self.text or not self._language_code)

    def _load_master_translation(self):
        if self._master_translation_id and not self._master_translation_cache:
            self._master_translation_cache = MasterTranslation.objects.get(
                pk=self._master_translation_id
            )

            self._text = self._master_translation_cache.text
            self._hint = self._master_translation_cache.hint
            self._language_code = self._master_translation_cache.language_code

    def _clear_master_translation(self):
        self._master_translation_id = None
        self._master_translation_cache = None

    @property
    def text(self):
        self._load_master_translation()
        return self._text

    @text.setter
    def text(self, value):
        """ Return the original (not translated) master text. """
        if self._text != value:
            self._clear_master_translation()
        self._text = value

    @property
    def language_code(self):
        """ Returns the language code of the master text. """
        self._load_master_translation()
        return self._language_code

    @language_code.setter
    def language_code(self, language_code):
        if self._language_code != language_code:
            self._clear_master_translation()
        self._language_code = language_code

    @property
    def hint(self):
        self._load_master_translation()
        return self._hint

    @hint.setter
    def hint(self, value):
        if self._hint != value:
            self._clear_master_translation()
        self._hint = value

    def __unicode__(self):
        """ Return the text translated into the currently-active language.
            By automatically rendering the translated text it means that in terms of rendering in
            templates a TranslatableCharField can be treated the same as a CharField.
        """
        if not (self._text or self._hint):
            self._load_master_translation()
        return trans._get_trans(self._text, self._hint)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        short_text = self.text[:30]
        if len(self.text) > 30:
            short_text += u"…"
        as_unicode = u"<TranslatableContent '{}' lang: {}>".format(short_text, self.language_code)
        return as_unicode.encode("utf-8")

    def get_display(self):
        self._load_master_translation()
        if self._master_translation_cache:
            return self._master_translation_cache.get_display()
        return self.text

    def text_for_language_code(self, language_code):
        # We'll keep this, since maybe someone uses it, but language should be switched via
        # translation activate/deactivate
        self._load_master_translation()
        return trans._get_trans(self._text, self._hint, language_override=language_code)

    def save(self):
        if self.is_effectively_null:
            return None

        return MasterTranslation.objects.get_or_create(
            pk=MasterTranslation.generate_key(self.text, self.hint, self.language_code),
            defaults={
                "text": self.text,
                "hint": self.hint,
                "language_code": self.language_code
            }
        )[0]


class TranslatableCharField(models.ForeignKey):
    def __init__(self, to=None, hint=u"", group=None, *args, **kwargs):
        self.hint = hint
        self.group = group

        kwargs["related_name"] = "+" # Disable reverse relations
        kwargs["null"] = True # We need to make this nullable for translations which haven't been set yet
        if "on_delete" not in kwargs:
            kwargs["on_delete"] = models.DO_NOTHING

        # Only FK to MasterTranslation
        super(TranslatableCharField, self).__init__("fluent.MasterTranslation", *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(TranslatableCharField, self).deconstruct()

        del kwargs["related_name"]
        del kwargs["null"]

        if self.hint != u"":
            kwargs["hint"] = self.hint

        if self.group != None:
            kwargs["group"] = self.group

        return name, path, args, kwargs

    def formfield(self, **kwargs):
        from fluent.forms import TranslatableCharField
        defaults = {
            'form_class': TranslatableCharField,
            'hint': self.hint,
        }
        defaults.update(kwargs)

        # Call the Field formfield method with the defaults
        return models.Field.formfield(self, **defaults)

    def value_from_object(self, obj):
        return getattr(obj, self.name)

    def validate(self, value, model_instance):
        # Bypass the ForeignKey existence checking
        return models.Field.validate(self, value, model_instance)

    def to_python(self, value):
        if value is None:
            return TranslatableContent()

        if isinstance(value, basestring):
            # This exists solely for fixture loading of strings
            return TranslatableContent(
                text=value,
                hint=self.hint,
                language_code=settings.LANGUAGE_CODE
            )

        return value

    def pre_save(self, model_instance, add):
        # Get the translatable content instance
        content = getattr(model_instance, self.name)

        # Save it, creating the master translation if necessary
        # If content.is_effectively_null returns True then this returns None
        master_translation = content.save()

        if not master_translation and not self.blank:
            raise IntegrityError("You must specify a value for {}".format(self.name))

        # Set the underlying master translation ID
        setattr(
            model_instance,
            self.column,
            master_translation.pk if master_translation else None
        )

        if master_translation:
            assert master_translation.pk

            # Update the master translation cache field if there was a master translation
            # created
            getattr(model_instance, MASTERS_CACHE_ATTR)[master_translation.pk] = {
                'hint': master_translation.hint,
                'text': master_translation.text,
                'lang': master_translation.language_code,
            }

        # Then call up to the foreign key pre_save
        return super(TranslatableCharField, self).pre_save(model_instance, add)

    def contribute_to_class(self, cls, name, virtual_only=False):
        try:
            cls._meta.get_field(MASTERS_CACHE_ATTR)
        except FieldDoesNotExist:
            cache_field = JSONField(blank=True)
            cache_field.contribute_to_class(cls, MASTERS_CACHE_ATTR, virtual_only)

        # Do whatever foreignkey does
        super(TranslatableCharField, self).contribute_to_class(cls, name, virtual_only)

        # Get the klass of the descriptor that it used
        klass = getattr(cls, name).__class__

        CACHE_ATTRIBUTE = "{}_content".format(self.name)

        # Now, subclass it so we can add our own magic
        class TranslatableFieldDescriptor(klass):
            def __get__(self, instance, instance_type):
                # First, do we have a content attribute or non-None default already,
                # if so, return it
                existing = getattr(instance, CACHE_ATTRIBUTE, self.field.get_default())
                if existing:
                    return existing

                master_translation = None
                master_id = getattr(instance, self.field.attname)
                instance_cache = getattr(instance, MASTERS_CACHE_ATTR)
                master_data = instance_cache.get(master_id, None)

                # If there's a master_id assigned but it's not in the instance cache yet,
                # attempt to retrieve the related MasterTranslation
                if master_id and not master_data:
                    master_translation = super(TranslatableFieldDescriptor, self).__get__(instance, instance_type)
                    if master_translation:
                        master_data = instance_cache[master_id] = {
                            'text': master_translation.text,
                            'hint': master_translation.hint,
                            'lang': master_translation.language_code,
                        }

                if master_data:
                    # When master_data is coming from the instance cache the resulting
                    # TranslatableContent is crippled (the master_translation_cache is None),
                    # but it works fine for translations.
                    new_content = TranslatableContent()
                    new_content._master_translation_id = master_id
                    new_content._master_translation_cache = master_translation
                    new_content._hint = master_data['hint']
                    new_content._text = master_data['text']
                    new_content._language_code = master_data['lang']
                else:
                    new_content = TranslatableContent(hint=self.field.hint)

                setattr(instance, CACHE_ATTRIBUTE, new_content)
                return new_content

            def __set__(self, instance, value):
                if not isinstance(value, TranslatableContent):
                    raise ValueError("Must be a TranslatableContent instance")

                # If no hint is specified, but we have a default, then set it
                value.hint = value.hint or self.field.hint

                # Replace the content attribute
                setattr(instance, CACHE_ATTRIBUTE, value)

                # If this is new, never before seen content, then _master_translation_id
                # will be None, so we don't want to set anything in the master translation
                # cache field
                if value._master_translation_id:
                    # Update the instance master translation cache
                    getattr(instance, MASTERS_CACHE_ATTR)[value._master_translation_id] = {
                        'hint': value.hint,
                        'text': value.text,
                        'lang': value.language_code,
                    }

                # Make sure we update the underlying master translation appropriately
                super(TranslatableFieldDescriptor, self).__set__(instance, value._master_translation_id)

        setattr(cls, self.name, TranslatableFieldDescriptor(self))

    def get_default(self):
        val = super(TranslatableCharField, self).get_default()

        # default value might be None (blank=True)
        if not isinstance(val, TranslatableContent) and val is not None:
            raise ValueError("Default value of {} must be a TranslatableContent instance".format(self.name))

        return val

    # Model mummy fix to always force creation
    @property
    def fill_optional(self):
        return True

    @fill_optional.setter
    def fill_optional(self, value):
        # We are going to ignore model mummy decision, keep it True
        pass


class TranslatableTextField(TranslatableCharField):

    def formfield(self, **kwargs):
        # override the default form widget to be a textarea
        defaults = {
            'widget': forms.Textarea,
        }
        defaults.update(kwargs)
        return super(TranslatableTextField, self).formfield(**defaults)


def find_installed_translatable_fields(with_groups=None):
    """
        Scans Django's model registry to find all the Translatable(Char|Text)Fields in use,
        along with their models. This allows us to query for all master translations
        with a particular group.
    """
    # FIXME: Internal API, should find a nicer way
    all_fields = MasterTranslation._meta._relation_tree

    translatable_fields_by_model = {}
    for field in all_fields:
        # Note that TranslatableTextField is a subclass of TranslatableCharField, so this works fine
        if isinstance(field, TranslatableCharField):
            # If groups specified, check membership
            if with_groups and field.group not in with_groups:
                continue
            if field.model not in translatable_fields_by_model:
                translatable_fields_by_model[field.model] = []
            translatable_fields_by_model[field.model].append(field)

    return translatable_fields_by_model


@deprecated(find_installed_translatable_fields.__name__)
def find_all_translatable_fields(with_group=None):
    """
        Deprecated. Use find_installed_translatable_fields().
    """
    # Proxy to find_installed_translatable_fields and convert dict response to list of tuples
    translatable_fields = []
    if with_group:
        translatable_fields_by_model = find_installed_translatable_fields(with_groups=[with_group])
    else:
        translatable_fields_by_model = find_installed_translatable_fields()
    for model, mt_ids in translatable_fields_by_model.items():
        translatable_fields.extend([(model, mt_id) for mt_id in mt_ids])

    return translatable_fields
