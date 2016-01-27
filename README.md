# Fluent is a Dynamic Translation Library for Djangae

Django handles static translations pretty nicely with PO files, but if you need
your text to be instantly translatable without a redeployment you're a bit stuck.

This library allows you to edit your translations on-the-fly and have them immediately
update on the live site. You can also export translations to a file, or import them.

The library does the following:

 - Provides a new makemessages command which generates a JSON file containing your code
  and template translations which you should deploy with your app.
 - Provides Django admin extensions so you can update your translatable content in the datastore (WIP)
 - Provides {% trans %} and {% blocktrans %} overrides so you can categorize translatable text into groups
  for export or import
 - Provides a TranslatableField for representing a TextField which can be localized into multiple languages
 - Monkey-patches gettext and friends so your dynamic translations take effect


