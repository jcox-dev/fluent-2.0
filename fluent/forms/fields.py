from django import forms
from fluent.fields import TranslatableContent


class TranslatableField(object):
    def clean(self, value):
        value = super(TranslatableField, self).clean(value)
        if value:
            return TranslatableContent(
                text=value
            )


class TranslatableCharField(TranslatableField, forms.CharField):
    pass
