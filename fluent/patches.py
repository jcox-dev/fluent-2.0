from __future__ import unicode_literals
import sys
import os

from importlib import import_module

from .trans import (
    gettext,
    ugettext,
    pgettext,
    ngettext,
    ungettext,
    npgettext,
    gettext_lazy,
    ugettext_lazy,
    pgettext_lazy,
    ngettext_lazy,
    ungettext_lazy,
    npgettext_lazy
)


try:
    #Define a generator if model_mommy is available
    from model_mommy import random_gen

    mommy_available = True
    def gen_translatablecontent():
        from fluent.fields import TranslatableContent
        return TranslatableContent(text=random_gen.gen_text())
except ImportError:
    mommy_available = False


def monkey_patch():
    from django.conf import settings
    from django.template import base
    base.ugettext_lazy = ugettext_lazy
    base.pgettext_lazy = pgettext_lazy

    from django.utils import translation
    translation.gettext = gettext
    translation.ugettext = ugettext
    translation.pgettext = pgettext
    translation.ngettext = ngettext
    translation.ungettext = ungettext
    translation.npgettext = npgettext
    translation.gettext_lazy = gettext_lazy
    translation.ugettext_lazy = ugettext_lazy
    translation.pgettext_lazy = pgettext_lazy
    translation.ngettext_lazy = ngettext_lazy
    translation.ungettext_lazy = ungettext_lazy
    translation.npgettext_lazy = npgettext_lazy

    from django.conf import locale as locale_mod
    BASE_INFO = dict(locale_mod.LANG_INFO)
    for additional_path in settings.LOCALE_PATHS:
        try:
            temp_path, imp = os.path.split(additional_path)
            sys.path.insert(0, temp_path)
            additional_mod = import_module(imp)
            sys.path.pop(0)
        except ImportError as e:
            raise ImportError("Could not import additional locale '%s': %s" % (additional_path, e))
        BASE_INFO.update(additional_mod.LANG_INFO)

    locale_mod.LANG_INFO = BASE_INFO

    if mommy_available:
        if not getattr(settings, 'MOMMY_CUSTOM_FIELDS_GEN', None):
            settings.MOMMY_CUSTOM_FIELDS_GEN = {}

        for field in ('TranslatableCharField', 'TranslatableTextField'):
            field_path = 'fluent.fields.%s' % field
            if field_path not in settings.MOMMY_CUSTOM_FIELDS_GEN:
                settings.MOMMY_CUSTOM_FIELDS_GEN[field_path] = gen_translatablecontent
