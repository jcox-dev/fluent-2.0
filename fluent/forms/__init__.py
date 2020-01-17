from __future__ import unicode_literals

from builtins import object
from .fields import TranslatableCharField
from . import widgets


class ModelAdminMixin(object):
    def __init__(self, *args, **kwargs):
        from .. import fields

        super(ModelAdminMixin, self).__init__(*args, **kwargs)
        self.formfield_overrides[fields.TranslatableCharField] = { 'form_class': TranslatableCharField }
        self.formfield_overrides[fields.TranslatableTextField] = {
            'form_class': TranslatableCharField,
            'widget': widgets.TranslatableTextField
        }

    def formfield_for_dbfield(self, db_field, **kwargs):
        ret = super(ModelAdminMixin, self).formfield_for_dbfield(db_field, **kwargs)
        if isinstance(ret, TranslatableCharField):
            ret.widget.can_add_related = False
            ret.widget.can_change_related = False
            ret.widget.can_delete_related = False
        return ret
