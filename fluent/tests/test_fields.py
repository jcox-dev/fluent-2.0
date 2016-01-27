
from django.db import models
from djangae.test import TestCase

from fluent.fields import TranslatableField

class TestModel(models.Model):
    class Meta:
        app_label = "fluent"


    trans = TranslatableField()
    trans_with_hint = TranslatableField(hint="Test")
    trans_with_group = TranslatableField(group="Test")


class TranslatableFieldTests(TestCase):

    def test_unset_translations(self):
        m = TestModel.objects.create()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)

        m.save()

        self.assertEqual("", m.trans.text)
        self.assertEqual("", m.trans_with_hint.text)
        self.assertEqual("", m.trans_with_group.text)

    def test_setting_translation_text(self):
        m = TestModel()
        m.trans.text = "Hello World!"
        m.trans_with_group.text = "Hello World!"
        m.trans_with_hint.text = "Hello World!"
        m.save()
