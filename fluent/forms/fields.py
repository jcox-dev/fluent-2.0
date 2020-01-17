from __future__ import unicode_literals
from past.builtins import basestring
from django import forms
from django.conf import settings

from . import widgets


class TranslatableCharField(forms.CharField):
    """ Form field for the TranslatableCharField and TranslatableTextField model fields.
        They both use this same form field but specify different widgets.
    """
    def __init__(self, language_code=None, hint=u"", *args, **kwargs):
        self.language_code = language_code or settings.LANGUAGE_CODE
        self.hint = hint
        kwargs.setdefault("widget", widgets.TranslatableCharField())
        super(TranslatableCharField, self).__init__(*args, **kwargs)

    def clean(self, value):
        from fluent.fields import TranslatableContent

        if isinstance(value, TranslatableContent):
            value.text = super(TranslatableCharField, self).clean(value.text)

            if not value.hint:
                value.hint = self.hint
            if not value.language_code:
                value.language_code = self.language_code
            return value
        elif isinstance(value, basestring):
            value = super(TranslatableCharField, self).clean(value)

            return TranslatableContent(
                text=value,
                hint=self.hint,
                language_code=self.language_code
            )
        else:
            return TranslatableContent(hint=self.hint, language_code=self.language_code)
