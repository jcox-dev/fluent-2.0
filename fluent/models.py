from hashlib import md5

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from djangae.db import transaction
from djangae.fields import JSONField, RelatedSetField, SetField, ComputedCharField

from fluent.cldr.rules import get_plural_index
from fluent.cldr.validation import validate_translation_texts
from fluent.utils import find_closest_supported_language


class ScanMarshall(models.Model):
    files_left_to_process = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton

        # You can create the ScanMarshall object without a count, but once
        # you save it again without one it means we reached the end of processing
        # so we remove the marshal object
        if self.files_left_to_process == 0 and not self._state.adding:
            self.delete()
        else:
            return super(ScanMarshall, self).save(*args, **kwargs)

    class Meta:
        app_label = "fluent"


class Translation(models.Model):
    master_translation = models.ForeignKey("fluent.MasterTranslation", editable=False, related_name="+")
    language_code = models.CharField(max_length=8, blank=False)

    plural_texts = JSONField(blank=True)  # These are the various plural translations depending on the language

    denorm_master_text = models.TextField(editable=False)
    denorm_master_hint = models.CharField(max_length=500, editable=False)
    denorm_master_language = models.CharField(max_length=8, editable=False)

    master_text_hint_hash = models.CharField(max_length=64)

    class Meta:
        app_label = "fluent"

    @property
    def text(self):
        singular_form = get_plural_index(self.language_code, 1)
        try:
            return self.plural_texts[singular_form]
        except KeyError:
            # Some kind of corrupt data, so just return the source language
            return self.denorm_master_text

    @text.setter
    def text(self, value):
        singular_form = get_plural_index(self.language_code, 1)
        self.plural_texts[singular_form] = value

    def clean(self):
        msgs = validate_translation_texts(self)
        if msgs:
            raise ValidationError([err for err, _orig, _trans in msgs])

    @staticmethod
    def generate_hash(master_text, master_hint):
        assert master_text
        assert master_hint is not None

        result = md5()
        for x in (master_text, master_hint):
            x = x.encode('utf-8')
            result.update(x)
        return result.hexdigest()

    def save(self, *args, **kwargs):
        assert self.language_code
        assert self.master_translation_id
        assert len(self.plural_texts)

        self.denorm_master_text = self.master_translation.text
        self.denorm_master_hint = self.master_translation.hint
        self.denorm_master_language = self.master_translation.language_code

        # For querying (you can't query for text on the datastore)
        self.master_text_hint_hash = Translation.generate_hash(
            self.denorm_master_text,
            self.denorm_master_hint
        )
        super(Translation, self).save(*args, **kwargs)


class MasterTranslation(models.Model):
    id = models.CharField(max_length=64, primary_key=True)

    text = models.TextField()
    text_for_ordering = ComputedCharField(lambda instance: instance.text[:500], max_length=500)

    plural_text = models.TextField(blank=True)
    hint = models.CharField(max_length=500, default="", blank=True)

    language_code = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE
    )

    translations_by_language_code = JSONField()
    translations = RelatedSetField(Translation)
    translated_into_languages = SetField(models.CharField(max_length=8), editable=False)

    # Was this master translation updated or created by make messages?
    used_in_code_or_templates = models.BooleanField(default=False, blank=True, editable=False)

    # Were any groups specified in the trans tags?
    used_by_groups_in_code_or_templates = SetField(models.CharField(max_length=64), blank=True)

    # Record the ID of the last scan which updated this instance (if any)
    last_updated_by_scan_uuid = models.CharField(max_length=64, blank=True, default="")

    first_letter = models.CharField(max_length=1, editable=False)

    @property
    def is_plural(self):
        return bool(self.plural_text)

    def __unicode__(self):
        return u"{} ({}{})".format(self.text, self.language_code, ' plural' if self.is_plural else '')

    def text_for_language_code(self, lang_code):
        new_code = find_closest_supported_language(lang_code)
        if new_code not in self.translations_by_language_code.keys():
            # we don't have a translation for this language
            return self.text

        translation_id = self.translations_by_language_code[new_code]
        translation = Translation.objects.get(id=translation_id)

        return translation.text

    @classmethod
    def find_by_group(cls, group_name):
        from .fields import find_all_translatable_fields
        translatable_fields = find_all_translatable_fields(with_group=group_name)

        # Go through all Translatable(Char|Text)Fields or TextFields marked with the specified group and get
        # all the master translation IDs which are set to them
        master_translation_ids = []
        for model, field in translatable_fields:
            master_translation_ids.extend(
                model.objects.values_list(field.attname, flat=True)
            )
            master_translation_ids = list(set(master_translation_ids))

        # Now get all the master translations with a group specified in the templates
        master_translation_ids.extend(
            list(MasterTranslation.objects.filter(used_by_groups_in_code_or_templates=group_name).values_list("pk", flat=True))
        )

        # Make sure master translation ids don't include None values or duplicates
        master_translation_ids = set(master_translation_ids)
        master_translation_ids = master_translation_ids - {None}
        # Return them all!
        return MasterTranslation.objects.filter(pk__in=master_translation_ids)

    @staticmethod
    def generate_key(text, hint, language_code):
        assert text
        assert hint is not None
        assert language_code

        result = md5()
        for x in (text.encode("utf-8"), hint.encode("utf-8"), language_code):
            result.update(x)
        return result.hexdigest()

    def save(self, *args, **kwargs):
        assert self.text
        assert self.language_code

        # Always store the first letter for querying
        self.first_letter = self.text[0]

        # Generate the appropriate key on creation
        if self._state.adding:
            self.pk = MasterTranslation.generate_key(
                self.text, self.hint, self.language_code
            )

        # If we are adding for the first time, then create a counterpart
        # translation for the master language.

        # Note that this Translation will be complete and correct only for the languages that
        # only require 2 plural forms - for others this language needs to be explicitly translated
        # or updated later.
        if self._state.adding:
            with transaction.atomic(xg=True):

                singular_form = get_plural_index(self.language_code, 1)
                plural_form = get_plural_index(self.language_code, 2)

                plurals = {singular_form: self.text}
                if self.is_plural:
                    plurals[plural_form] = self.plural_text

                # if len(LANGUAGE_LOOKUPS[self.language_code].plurals_needed) > len(plurals):
                # FIXME: We can detect that we're dealing with a language that needs more plurals
                # What should we do? mark the translation as incomplete?
                # Don't create the translation object at all?
                new_trans = Translation.objects.create(
                    master_translation=self,
                    language_code=self.language_code,
                    plural_texts=plurals,
                    denorm_master_text=self.text,
                    denorm_master_hint=self.hint
                )
                self.translations_by_language_code[self.language_code] = new_trans.pk
                self.translations.add(new_trans)

                self.translated_into_languages = set(self.translations_by_language_code.keys())
                return super(MasterTranslation, self).save(*args, **kwargs)
        else:
            # Otherwise just do a normal save
            self.translated_into_languages = set(self.translations_by_language_code.keys())
            return super(MasterTranslation, self).save(*args, **kwargs)

    def create_or_update_translation(self, language_code, singular_text=None, plural_texts=None, validate=False):

        with transaction.atomic(xg=True):
            trans = None
            if language_code in self.translations_by_language_code:
                # We already have a translation for this language, update it!
                try:
                    trans = Translation.objects.get(pk=self.translations_by_language_code[language_code])
                    created = False
                except Translation.DoesNotExist:
                    trans = None

            if not trans:
                # OK, create the translation object and add it to the respective fields
                trans = Translation(
                    master_translation_id=self.pk,
                    language_code=language_code,
                    denorm_master_hint=self.hint,
                    denorm_master_text=self.text
                )
                created = True

            if plural_texts:
                trans.plural_texts = plural_texts
            else:
                trans.text = singular_text

            if validate:
                errors = validate_translation_texts(trans, self)
                if errors:
                    return errors

            trans.master_translation = self
            trans.save()

            if created:
                self.refresh_from_db()
                self.translations_by_language_code[language_code] = trans.pk
                self.translations.add(trans)
                self.save()

    class Meta:
        app_label = "fluent"
