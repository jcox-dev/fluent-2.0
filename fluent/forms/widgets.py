from django.conf import settings
from django.forms.widgets import (
    MultiWidget,
    TextInput,
    Textarea,
    Select
)

from fluent.fields import TranslatableContent


class TranslatableWidget(MultiWidget):
    """
        A split widget which allows entering text for a master translation
        and the language code that the text is in.
    """
    def decompress(self, value):
        return value.text, value.language_code

    def value_from_datadict(self, data, files, name):
        text, language_code = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)
        ]
        return TranslatableContent(text=text, language_code=language_code)


class TranslatableCharField(TranslatableWidget):
    #HACK! Django assumes that because it's a ForeignKey, that it has choices :(
    choices = tuple()

    def __init__(self, attrs=None, *args, **kwargs):
        widgets = (
            TextInput(attrs),
            Select(attrs, choices=settings.LANGUAGES)
        )
        super(TranslatableCharField, self).__init__(widgets, attrs)


class TranslatableTextField(TranslatableWidget):
    choices = tuple()

    def __init__(self, attrs=None, *args, **kwargs):
        widgets = (
            Textarea(attrs),
            Select(attrs, choices=settings.LANGUAGES)
        )
        super(TranslatableTextField, self).__init__(widgets, attrs)
