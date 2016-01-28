from django import forms
from django.conf import settings

from fluent.fields import TranslatableContent


class TranslatableField(object):
    def __init__(self, language_code=None, hint=u"", *args, **kwargs):
        self.language_code = language_code or settings.LANGUAGE_CODE
        self.hint = hint
        super(TranslatableField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(TranslatableField, self).clean(value)
        if value:
            return TranslatableContent(
                text=value,
                hint=self.hint,
                language_code=self.language_code
            )
        else:
            return TranslatableContent(hint=self.hint, language_code=self.language_code)


class TranslatableCharField(TranslatableField, forms.CharField):
    pass
