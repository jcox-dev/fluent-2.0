""" CLDR/ICU pluralization support.

ICU/ARB plurals support
=======================

Out `Translation` objects have a JSON `plurals` field which holds the plural forms. There are
six case keywords which hold message versions depending on the number: zero, one, two, few, many, other.
If a value is missing for anyone of them `other` is used.
Additionally the JSON value may hold message versions for explicit cases (=1, =42).

#TODO (this is what the specs say, but it'll be done in ticket #952)
When we're looking up a number N, we check if `plurals` holds a specific =N case, and use it.
If it doesn't we pass N through the plural_rules code to determine the case keyword to use.

The specs addtionally define how to substitute the `#` character for a locale formatted N value, but
we're ignoring that part and simply expect a normal ARB curly braced placeholder for the value.


Singular translations
=====================

For singular translations we'll always keep the translated text in `plurals[ONE]` that way we
can eventually get rid of all the other fields on the `Translation` model.


Examples and Docs
=================

How this actually works:

(http://icu-project.org/apiref/icu4j/com/ibm/icu/text/PluralFormat.html)

Pluralization rules:

http://www.unicode.org/cldr/charts/latest/supplemental/language_plural_rules.html


"{COMB_OF_GENDER_AND_PLURAL,
    select,
    female {{
        NUM_VALUES, plural, =1 {Category} other {Categories}
    }}
    male {{
        NUM_VALUES, plural, =1 {Category} other {Categories}
    }}
    other {{
        NUM_VALUES, plural, =1 {Category} other {Categories}
    }}
}",


"{NUM_EMAILS_TO_SEND, plural, =0 {unused plural form} =1 {One email will be sent.} other {# emails will be sent.}}"


Gettext support
===============

We're keeping the internal representation closer to the cldr rules because they're more complex and verbose
(explicit ONE, ZERO, FEW, MANY) forms. Gettext uses a simpler approach with an indexed list of forms and a simple
function for computing the index. There might be some convention to the order of plural forms for languages,
so instead of generating the indexed form from our representation we manually match a Gettext
plural form definition from here http://localization-guide.readthedocs.org/en/latest/l10n/pluralforms.html
to our cldr functions.

Using that we can match indexed ordered forms to codenamed cldr forms allowing for *.po import and export.

"""
import re
from decimal import Decimal, InvalidOperation
from .models import RE_NAMED_SYMBOLS
from django.utils.datastructures import SortedDict

from .cldr_rules import LANGUAGE_LOOKUPS, get_plural_index


# Trying to keep the the data small
_json_kw = ZERO, ONE, TWO, FEW, MANY, OTHER = 'zotfmh'
_icu_kw = 'zero', 'one', 'two', 'few', 'many', 'other'
ICU_KEYWORDS = SortedDict(zip(_icu_kw, _json_kw))


RE_PYTHON_PLACEHOLDERS = RE_NAMED_SYMBOLS
RE_ICU_PLACEHOLDERS = re.compile(r'{([^}]+)}')

# Just a regular message, a string with curly braced variables
RE_ICU_MSG = re.compile(r'(^[^{}]*(?:{[A-Za-z_]+}[^{}]*)*$)')

# Something, something, plural forms
RE_ICU_PLURAL_MSG = re.compile(r'^{\s*[A-Za-z_]+\s*,\s*plural\s*,\s*(?P<plurals>.+)}$')


def _icu_encode(text):
    """ Changes placeholder representation from python to curly braces, and removes double percentages."""
    return RE_PYTHON_PLACEHOLDERS.sub(r"{\1}", text).replace('%%', '%')


def _icu_decode(text):
    """ Change placeholders into python's representation and double encode percentages."""
    return RE_ICU_PLACEHOLDERS.sub(r"%(\1)s", text.replace('%', '%%'))


def _export_plurals(plurals):
    """ Encode a plurals dict in ICU format.

    First the explicit `=1` directives, followed by the six ICU keyword messages (whichever
    of them exist in the data dictionry). """
    parts = ["{NUM, plural,"]
    keyword_parts = []
    for icu_key, key in ICU_KEYWORDS.items():
        if key in plurals:
            message = _icu_encode(plurals.pop(key))
            keyword_parts.append(" %s {%s}" % (icu_key, message))
    # The remaining keys in the dictionary are numbers
    for key in sorted(plurals.keys()):
        assert isinstance(key, (int, long))
        message = _icu_encode(plurals.pop(key))
        parts.append(" =%s {%s}" % (key, message))

    parts.extend(keyword_parts)
    parts.append("}")
    return "".join(parts)


def export_master_message(master):
    if not master.plural_text:
        return _icu_encode(master.text)
    # Assuming master is English and populate ONE and OTHER forms
    return _export_plurals({ONE: master.text, OTHER: master.plural_text})


def export_translation_message(trans, only_needed=False):
    #FIXME: this is only needed as long as we keep both `plurals` and `translated_text`+`plural_texts`
    if not trans.plurals:
        return _icu_encode(trans.translated_text)

    lookup_fun = LANGUAGE_LOOKUPS[trans.language_code.split("-")[0].lower()]
    if not trans.master.plural_text:
        singular_form = lookup_fun(1)
        return _icu_encode(trans.plurals[singular_form])

    if only_needed:
        plurals = dict((form, t) for (form, t) in trans.plurals.iteritems() if form in lookup_fun.plurals_needed)
    else:
        plurals = dict(trans.plurals)

    if len(plurals) == 1:
        # if there's only one plural form it has to be the singular translation
        return _icu_encode(plurals.values()[0])
    return _export_plurals(plurals)


def _decode_icu_plurals(data):
    """ Parse the ICU encoded plural options into a dictionary.

    The _msg_generator is simple tokenizer. Since we know the input is going to be:
    "keyword {blah {var} blah} ..." When we encounter an opening brace, we know we just
    finished reading a keyword. Inside the translated messages it would be enough to
    count opening and closing brackets, but since we know there can be at most two levels (msg + variables)
    we do the extra error checking (too many curly brace levels).

    Once the input is tokenized into keywords and translation messages, we validate the keywords.
    They must either be in ICU_KEYWORDS, or "=" + <number>.
    """
    result = {}
    OUTER, TRANS, TRANS_VAR = 0,1,2  # the possible nested braces levels
    def _msg_generator(chars):
        brace_level = 0
        buf = []
        for x in data:
            buf.append(x)
            if x == '{':
                # start buffering the translation
                brace_level += 1
                if brace_level > TRANS_VAR:
                    raise ValueError('Too many curly brace levels')
                if brace_level == TRANS:
                    # yield a keyword and start buffering a translation
                    buf.pop()
                    yield True, ''.join(buf).strip()
                    buf = []
            if x == '}':
                brace_level -= 1
                if brace_level < OUTER:
                    raise ValueError('Unexpected %s' % x)
                if brace_level == OUTER:
                    # A translation just ended, yield it and start buffering another keyword
                    buf.pop()
                    yield False, ''.join(buf)
                    buf = []
        if brace_level != OUTER:
            raise ValueError('Mismatched { } braces')
    last_keyword = None

    for is_keyword, token in _msg_generator(data):
        if not is_keyword:
            if last_keyword is None:
                raise ValueError('Expected a keyword')
            result[last_keyword] = _icu_decode(token)
            last_keyword = None
        else:
            if token[0] == '=':
                try:
                    # We attempt to parse as decimal to make sure it's a number
                    last_keyword = "=%s" % Decimal(token[1:])
                except InvalidOperation:
                    raise ValueError('Expected keyword: "=<number>", got: %s' % token)
            else:
                if token not in ICU_KEYWORDS:
                    raise ValueError('Expected %s or "=<number", got: "%s"' % (', '.join(_icu_kw), token))
                last_keyword = ICU_KEYWORDS[token]
    return result


def import_icu_message(msg, language=None):
    """ Decode the ICU message into a plurals dict. """
    if RE_ICU_MSG.match(msg):
        plural_form = get_plural_index(language, 1) if language else ONE
        return {plural_form: _icu_decode(msg)}
    # If the msg doesn't match a direct singular translation, attempt to decode as a plurals dict:
    match = RE_ICU_PLURAL_MSG.match(msg)
    data = match and match.group('plurals')
    if not data:
        raise ValueError('Incorrect ICU translation encoding')
    return _decode_icu_plurals(data)
