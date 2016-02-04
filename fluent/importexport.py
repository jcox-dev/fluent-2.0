#LIBRARIES
import time
import json

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.utils.datastructures import SortedDict

#FLUENT
from .validation import validate_translation_texts
from .models import MasterTranslation, Translation
from . import cldr
from .cldr_rules import LANGUAGE_LOOKUPS


def export_translations_as_arb(masters):
    response = HttpResponse(content_type="application/arb")
    response['Content-Disposition'] = 'attachment; filename="translations.arb"'

    data = SortedDict()
    data["@@locale"] = settings.LANGUAGE_CODE
    data["@@last_modified"] = timezone.now().strftime("%Y-%m-%dT%H:%M") + str.format('{0:+06.2f}', float(time.timezone) / 3600)

    for master in masters:
        key = str(master.pk)

        data[key] = cldr.export_master_message(master)
        data["@" + key] = {
            "type": "text",
            "source_text": cldr._icu_encode(master.text),
            "context": master.hint
        }

    response.write(json.dumps(data, indent=4))
    return response

'''
def export_translations_as_csv(masters):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="translations.csv"'

    writer = csv.writer(response, delimiter=",", quotechar='"')

    headings_written = False
    headings = []

    for trans in masters:
        row = [ trans.text.encode("utf-8"), trans.hint ]
        headings = [ "Text", "Context"]
        for code, desc in settings.LANGUAGES:
            if not headings_written: headings.append(code)

            if code in trans.translated_into_languages:
                row.append(trans.translations.get(language_code=code).translated_text.encode("utf-8"))

            else:
                row.append("")

        if not headings_written:
            writer.writerow(headings)
            headings_written = True
        writer.writerow(row)
    return response
'''


def get_needed_fields(plurals, language_code):
    lookup = LANGUAGE_LOOKUPS[language_code]
    missing = set(lookup.plurals_needed) - set(plurals)
    if missing:
        RK = dict((v, k) for (k, v) in cldr.ICU_KEYWORDS.items())
        raise ValueError("Missing keywords required by language: %s" % ', '.join(map(RK.get, missing)))
    return dict((keyword, form)
        for (keyword, form) in plurals.items()
        if keyword.startswith('=') or keyword in lookup.plurals_needed
    )


def import_translations_from_arb(file_in, language_code):
    """ ARB is json with original translations (which we ignore) and translated data which is
        provided as icu translated strings.

        The data keys should match our MasterTranslation pk's.
    """
    data = json.loads(file_in.read())
    errors = []

    for k, v in data.iteritems():
        if k.startswith("@") and not k.startswith("@@"):
            #Handle this translation
            try:
                pk = k.lstrip("@")
                master = MasterTranslation.objects.get(pk=pk)
            except MasterTranslation.DoesNotExist:
                errors.append(("Could not find translation: {0}".format(v['source_text']), 'unknown', ""))
                continue

            try:
                parsed_plurals = cldr.import_icu_message(data[str(pk)])
                plurals = get_needed_fields(parsed_plurals, language_code)
            except ValueError, e:
                errors.append((e.message, master.text, data[str(pk)]))
                continue

            # MasterTranslation.create_or_update_translation is repeated here, because we want
            # to validate the Translation and co
            if language_code in master.translations_by_language_code:
                translation = Translation.objects.get(pk=master.translations_by_language_code[language_code])
            else:
                translation = Translation(master_translation=master, language_code=language_code)

            translation.plural_texts = plurals
            errors.extend(validate_translation_texts(translation, master))
            if errors:
                continue
            translation.save()
    return errors

