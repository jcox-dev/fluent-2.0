import re
from fluent.cldr_rules import get_plural_index

# The NAMED_SYMBOL re is repeated in cldr_rules.PYTHON_
RE_FORMAT_SYMBOLS = re.compile(r'(?<!%)(?:%%)*%s')
RE_NAMED_SYMBOLS = re.compile(r'(?<!%)(?:%%)*%\(([^\)]+)\)s')


def compare_format_strings(a, b):
    """ Compares the number of positional arguments and the number and names of named placeholders."""
    msgs = []
    a_num = len(RE_FORMAT_SYMBOLS.findall(a))
    a_names = set(RE_NAMED_SYMBOLS.findall(a))
    b_num = len(RE_FORMAT_SYMBOLS.findall(b))
    b_names = set(RE_NAMED_SYMBOLS.findall(b))
    if a_num != b_num:
        msgs.append((u"Different number of positional arguments than the original text (%s != %s)." % (a_num, b_num), a, b))

    if a_names != b_names:
        if b_names - a_names:
            msgs.append((u"Extra placeholder name, missing from the original: %s" % ", ".join(b_names - a_names), a, b))
        if a_names - b_names:
            msgs.append((u"Missing placeholders from the original: %s" % ", ".join(a_names - b_names), a, b))
    return msgs


def validate_translation_texts(trans, master):
    if not master:
        master = trans.master_translation
    msgs = []
    singular_form = get_plural_index(trans.language_code, 1)
    for key, msg in trans.plural_texts.items():
        if not key.startswith("="):
            compare_to = master.text if key == singular_form else master.plural_text
            msgs.extend(compare_format_strings(compare_to, msg))
    return msgs
