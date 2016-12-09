# Fluent is a Dynamic Translation Library for [Djangae](https://github.com/potatolondon/djangae)

Django handles static translations pretty nicely with PO files, but on App Engine the filesystem is
not writeable, so if you need your text to be instantly translatable without a redeployment you're
a bit stuck.

This library is a replacement for Django's standard translation backend - allowing translations
which are defined in templates and Python files to be stored in the DB instead of in PO files,
thereby allowing the the translated text to be edited via the live site.  It also allows you to
have translations where the definitions (i.e. the default text) is stored on a model rather than
in a template or Python file.

As well as editing translations via the site, you can also export translations to a file, or
import them.

The library does the following:

 - Provides a web-based version of Django's `makemessages` command which scans the templates and
   Python files and stores translation definitions in the DB.  This is available via the Django
   admin.
 - Provides Django admin extensions so you can update your translatable content in the datastore.
 - Provides {% trans %} and {% blocktrans %} overrides so you can categorize translatable text into
   groups for export or import.
 - Provides a TranslatableCharField and TranslatableTextField for representing a TextField which
   can be localized into multiple languages.
 - Monkey-patches gettext and friends so that translations which are defined in your templates and
   Python files (or those of other third party apps) automatically use the Fluent backend.



## Installation

    pip install git+https://github.com/potatolondon/fluent-2.0.git#egg=fluent

Then add `'fluent'` to `settings.INSTALLED_APPS`.


## General Usage

* Set up `settings.LANGUAGES` and `settings.LANGUAGE_CODE` as normal.
* Add `'django.middleware.locale.LocaleMiddleware'` to `MIDDLEWARE_CLASSES`.
* Mark the translatable strings in your templates in the normal way using `{% trans %}` and
  `{% blocktrans %}` (see [Django docs](https://docs.djangoproject.com/en/dev/topics/i18n/translation/)).
  - Note that in addition to the normal parameters allowed by Django's tags, you can also add an
    optional `group` parameter to these tags to allow your translations to be split into groups for
    translating or exporting.  E.g. `{% trans "Submit" group "common" %}` or
    `{% blocktrans group "rarely-used" %}Arm the detonator{% endblocktrans %}`.
* Mark the translatable strings in your Python files in the normal way using
  `django.utils.translation.gettext` and friends.
  - As with the templates, you can optionally specify a `group` for each of these like that:
  `_('String', group='public')`
* In the Django admin, go to the _Fluent_ app and hit the _Start Scan_ button to start a background
  task that will scan your files for translatable text.
* You can also (or instead!) allow translatable text to be defined in values on models using
  `fluent.fields.TranslatableCharField` (or its friend `TranslatableTextField`).  This creates a
  field whose value is the "original" (default) text, which can then be translated.
* You can then use the exporting functionality (TODO!) to export files containing the translation
  definitions, and you can then imported the translated texts (also TODO).
* __NOTE__: The fluent trans and blocktrans tags will escape by default unlike the Django counterparts (see https://code.djangoproject.com/ticket/25872)
 if you do not want your translations escaped, you can pass "noescape" as an argument to the trans tag or opening blocktrans. This is done for security as
 translations are stored in the database and so could potentially be malliciously altered.



## TranslatableCharField & TranslatableTextField

* You can set a `hint` for each field that you put on a model, but this is really a _default_ hint,
  as you can optionally allow this hint to be edited, just like the text string that's stored in
  the field.
* The fields take an optional `language_code` argument which tells Fluent what language the
  original text is in.  This defaults to `settings.LANGUAGE_CODE`, but like the `hint` it can be
  dynamically set when setting the text value.
* The fields take an optional `group` argument.  Unlike the `hint`, this is not stored as part of
  the field's value and cannot be edited.
* When you add a `Translatable(Char|Text)Field` to a model, the attribute value becomes a
  `TranslatableContent` object (much like when you use Django's `FileField` you get a `FieldFile`
  object as the accessible attribute).  The `TranslatableContent` object has the following attribtes:
    - `text` - the translatable text (i.e. the default text).
    - `hint` - the hint for the translation.
    - `language_code` - the language of the translatable (default) text.
* The `TranslatableCharField` and `TranslatableTextField` differ only in the form field widget that
  they create on a ModelForm.


#### Translatable Fields Example Usage

```python

# models.py
from django.db import models
from fluent.fields import TranslatableCharField, TranslatableTextField

class NewsArticle(models.Model):

    title = TranslatableCharField(hint="The title of a news article")
    content = TranslatableTextField(hint="The content of a news article")
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User)

    def save(self, *args, **kwargs):
        # set the language of the translatable fields based on the author
        self.title.language_code = self.author.native_language
        self.content.language_code = self.author.native_language
        return super(NewsArticle, self).save(*args, **kwargs)


# views.py
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language

def serve_article(request, pk):
    article = get_object_or_404(NewsArticle, pk=pk)
    lang = get_language()
    context = dict(
        title=article.title.text_for_language_code(lang),
        content=article.content.text_for_language_code(lang),
    )
    return render(request, "article.html", context)
```


#### Further Examples

When passing the value of a TranslatableCharField into the model's init method, or setting the value directly by assignment, you must set the value as a TranslatableContent instance.

```python
from django.db import models
from fluent.fields import TranslatableCharField, TranslatableContent

class NewsArticle(models.Model):
    title = TranslatableCharField()

instance = NewsArticle(title=TranslatableContent("Squirrels Build Nut Factory"))

instance2 = NewsArticle()
instance2.title=TranslatableContent("Squirrels Build Bigger Nut Factory"))
```

## Escaping Behaviour

The HTML escaping behaviours of Fluent's `{% trans %}` and `{% blocktrans %}` tags are slightly different to Django's.

**Django Behaviour**

* `{% trans %}`
    - Default text is assumed to be safe and is not escaped.  HTML entities in the default text must be entered in their escaped form (e.g. `&lt;` rather than `<`) and the .po files will contain the escaped entities.
    - Translated text (from .po files) is **not** assumed to not be safe and is escaped.
    - Translators must therefore convert escaped HTML entities back to their un-escaped form.
* `{% blocktrans %}`
    - Makes an unwritten assumption that the content can contain HTML.
    - Default content is not escaped.  (Same as the `trans` tag.)
    - But unlike the `trans` tag, translated text is not escaped either.
    - Translators need to know **not** to convert escaped HTMl entities back to their unescaped forms.  But .po files do not provide a way to know which translations came from `trans` tags and which came from `blocktrans`.
    - Variables used within the content are escaped as normal.

**Fluent Behaviour**

* `{% trans %}`
    - Both default text and translated text are escaped, unless you pass the 'noescape' flag, in which case neither are escaped.
* `{% blocktrans %}`
    - Both default content and translated content are escaped, unless you pass the 'noescape' flag, in which case neither are escaped.
    - Variables used within the content are escaped as normal.


## Running tests

Install test dependencies:

```
./install_deps.py
```

Now, to run tests:
```
./runtests.py
```
