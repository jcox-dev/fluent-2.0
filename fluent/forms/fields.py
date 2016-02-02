from django import forms
from django.conf import settings

from fluent.fields import TranslatableContent


class TranslatableCharField(forms.CharField):
    """ Form field for the TranslatableCharField and TranslatableTextField model fields.
        They both use this same form field but specify different widgets.
    """
    def __init__(self, language_code=None, hint=u"", *args, **kwargs):
        self.language_code = language_code or settings.LANGUAGE_CODE
        self.hint = hint
        super(TranslatableCharField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(TranslatableCharField, self).clean(value)
        if value:
            return TranslatableContent(
                text=value,
                hint=self.hint,
                language_code=self.language_code
            )
        else:
            return TranslatableContent(hint=self.hint, language_code=self.language_code)
