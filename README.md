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
 - Provides a TranslatableField for representing a TextField which can be localized into multiple
   languages.
 - Monkey-patches gettext and friends so that translations which are defined in your templates and
   Python files (or those of other third party apps) automatically use the Fluent backend.


