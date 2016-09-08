# -*- coding: utf8 -*-
from django.conf import settings
from django.db import models
from django.db import IntegrityError
from django import forms

from .models import MasterTranslation
from .forms import widgets


class TranslatableContent(object):
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
        if self._text != value:
            self._clear_master_translation()
        self._text = value

    @property
    def language_code(self):
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
        self._load_master_translation()
        return self.text

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
        self._load_master_translation()
        if self._master_translation_cache:
            return self._master_translation_cache.text_for_language_code(language_code)
        else:
            # we don't have a master translation (or it failed to load)
            return self.text

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
    def __init__(self, hint=u"", group=None, *args, **kwargs):
        self.hint = hint
        self.group = group

        kwargs["related_name"] = "+" # Disable reverse relations
        kwargs["null"] = True # We need to make this nullable for translations which haven't been set yet

        # Only FK to MasterTranslation
        super(TranslatableCharField, self).__init__(MasterTranslation, *args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(TranslatableCharField, self).deconstruct()

        del kwargs["to"]
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

        # Then call up to the foreign key pre_save
        return super(TranslatableCharField, self).pre_save(model_instance, add)

    def contribute_to_class(self, cls, name, virtual_only=False):
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

                # If we don't, but we do have a master translation, then create a new content
                # attribute from that
                master_translation = super(TranslatableFieldDescriptor, self).__get__(instance, instance_type)
                if master_translation:
                    new_content = TranslatableContent(
                        hint=self.field.hint,
                        master_translation_id=master_translation.pk
                    )

                    # This avoids another lookup on accessing attributes of the content
                    new_content.text = master_translation.text
                    new_content.hint = master_translation.hint
                    new_content.language_code = master_translation.language_code
                    new_content._master_translation_cache = master_translation

                    setattr(instance, CACHE_ATTRIBUTE, new_content)
                else:
                    # Just set an empty Content as the cached attribute
                    setattr(instance, CACHE_ATTRIBUTE, TranslatableContent(hint=self.field.hint))

                # Return the content attribute
                return getattr(instance, CACHE_ATTRIBUTE)

            def __set__(self, instance, value):
                if not isinstance(value, TranslatableContent):
                    raise ValueError("Must be a TranslatableContent instance")

                # If no hint is specified, but we have a default, then set it
                value.hint = value.hint or self.field.hint

                # Replace the content attribute
                setattr(instance, CACHE_ATTRIBUTE, value)

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


def find_all_translatable_fields(with_group=None):
    """
        Scans Django's model registry to find all the Translatable(Char|Text)Fields in use,
        along with their models. This allows us to query for all master translations
        with a particular group.
    """

    # FIXME: Internal API, should find a nicer way
    all_fields = MasterTranslation._meta._relation_tree

    # Note that TranslatableTextField is a subclass of TranslatableCharField, so this works fine
    translatable_fields = [x for x in all_fields if isinstance(x, TranslatableCharField) ]

    if with_group is None:
        return [ (x.model, x) for x in translatable_fields ]
    else:
        # Filter by group
        return [ (x.model, x) for x in translatable_fields if x.group == with_group ]
