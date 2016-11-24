import re
import uuid
import os
import logging
import django
from django.apps import apps
from django.conf import settings
from django.utils.text import smart_split
from django.utils.translation import trim_whitespace

from djangae.db import transaction

from fluent.models import MasterTranslation, ScanMarshall

from google.appengine.ext.deferred import defer

logger = logging.getLogger(__file__)

DEFAULT_TRANSLATION_GROUP = "website"


def parse_file(content, extension):
    """
        Returns a list of (text, hint) tuples
    """
    TRANS_TAG_REGEX = [
        r"""\{%\s*trans\s+""" #{% trans
        r"""(?P<text>(?:".[^"]*?")|(?:'.[^']*?'))""" #The text string, in single or double quotes
        r"""(\s+context\s+(?P<hint>(?:".[^"]*?")|(?:'.[^']*?')))?""" #The context of the translation
        r"""(\s+as\s+\w+)?""" # Any alias e.g. as banana
        r"""(\s+group\s+(?P<group>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""\s*%\}""", # {% trans "things" as stuff%}
    ]

    REGEXES = [
        r"""\b(_|pgettext_lazy|gettext|pgettext|ugettext|ugettext_lazy)\(\s*"""
        r"""(?P<text>(?:".[^"]*?")|(?:'.[^']*?'))"""
        r"""(\s*,\s*(?P<hint>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""(\s*,\s*group\s*=\s*(?P<group>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""\s*\)"""
    ]

    NREGEXES = [
        r"""\b(_|npgettext_lazy|ngettext|npgettext|ungettext|ungettext_lazy)\(\s*"""
        r"""(?P<text>(?:".[^"]*?")|(?:'.[^']*?'))"""
        r"""(\s*,\s*(?P<plural>(?:".[^"]*?")|(?:'.[^']*?')))"""
        r"""(\s*,\s*(?P<count>\d+))"""
        r"""(\s*,\s*(?P<hint>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""(\s*,\s*group\s*=\s*(?P<group>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""\s*\)"""
    ]

    TEMPLATE_VAR_RE = re.compile(r'{{\s*([_a-zA-Z]+)\s*}}')

    def _strip_quotes(text):
        if not text:
            return text

        if text[0] == text[-1] and text[0] in "'\"":
            return text[1:-1]

        return text

    def find_trans_nodes(tokens, output):
        start_tag = None
        buf = []
        plural_buf = []
        in_plural = False
        group = DEFAULT_TRANSLATION_GROUP
        context = None

        for i, (token_type, token) in enumerate(tokens):
            parts = list(smart_split(token))

            if "endblocktrans" in parts:
                buf_joined = "".join(buf)
                plural_buf_joined = "".join(plural_buf)
                if "trimmed" in list(smart_split(start_tag)):
                    buf_joined = buf_joined.strip()
                    plural_buf_joined = plural_buf_joined.strip()
                output.append((start_tag, buf_joined, plural_buf_joined, context or u"", group))
                start_tag = None
                buf = []
                plural_buf = []
                in_plural = False
                context = ""
                group = DEFAULT_TRANSLATION_GROUP

            elif "blocktrans" in parts:
                start_tag = token

                try:
                    context = _strip_quotes(parts[parts.index("context") + 1])
                except ValueError:
                    context = None

                try:
                    group = _strip_quotes(parts[parts.index("group") + 1])
                except ValueError:
                    group = DEFAULT_TRANSLATION_GROUP

            elif "{%plural%}" in token.replace(" ", ""):
                in_plural = True

            elif start_tag:
                # Convert django {{ vars }} into gettext friendly %(vars)s
                part = TEMPLATE_VAR_RE.sub(r'%(\1)s', token)
                # Escape lone percentage signs
                part = re.sub(u'%(?!\()', u'%%', part)

                start_tag_parts = list(smart_split(start_tag))
                if start_tag_parts[1] == "blocktrans" and "trimmed" in start_tag_parts:
                    part = trim_whitespace(part)

                if not in_plural:
                    buf.append(part)
                else:
                    plural_buf.append(part)

            elif "trans" in token:
                match = re.compile(TRANS_TAG_REGEX[0]).match(token)
                if match:
                    group = _strip_quotes(match.group('group')).strip() if match.group('group') else DEFAULT_TRANSLATION_GROUP
                    hint = _strip_quotes(match.group('hint') or u"")
                    output.append( (match.group(0), _strip_quotes(match.group('text')), u"", hint, group) )

    def tokenize(inp):
        from django.template.base import (
            tag_re, VARIABLE_TAG_START,
            BLOCK_TAG_START, COMMENT_TAG_START,
            TRANSLATOR_COMMENT_MARK, TOKEN_TEXT,
            TOKEN_COMMENT, TOKEN_VAR, TOKEN_BLOCK
        )

        def create_token(token_string, in_tag):
            """ This is pretty similar to Django's Lexer.tokenize()
            except we don't strip the strings, so we can recreate the content
            of block tags exactly"""

            if in_tag:
                if token_string.startswith(VARIABLE_TAG_START):
                    return (TOKEN_VAR, token_string)
                elif token_string.startswith(BLOCK_TAG_START):
                    return (TOKEN_BLOCK, token_string)
                elif token_string.startswith(COMMENT_TAG_START):
                    content = ""
                    if token_string.find(TRANSLATOR_COMMENT_MARK):
                        content = token_string
                    return (TOKEN_COMMENT, content)
            else:
                return (TOKEN_TEXT, token_string)

        in_tag = False
        result = []

        for bit in tag_re.split(inp):
            if bit:
                result.append(create_token(bit, in_tag))
            in_tag = not in_tag
        return result


    if extension in (".html",):
        tokens = tokenize(content)
        output = []
        find_trans_nodes(tokens, output)

        results = []
        for tag, text, plural_text, hint, group in output:
            results.append((text, plural_text, hint, group))

        return results
    else:
        results = []
        for regex in REGEXES:
            result = re.compile(regex).finditer(content)
            for match in result:
                text = _strip_quotes(match.group('text'))

                try:
                    hint = match.group('hint') or u""
                except IndexError:
                    hint = u""
                    
                try:
                    group = _strip_quotes(match.group('group')) or DEFAULT_TRANSLATION_GROUP
                except IndexError:
                    group = DEFAULT_TRANSLATION_GROUP

                hint = _strip_quotes(hint)
                results.append((text, "", hint, group))

        for regex in NREGEXES:
            result = re.compile(regex).finditer(content)
            for match in result:
                text = _strip_quotes(match.group('text'))
                plural = _strip_quotes(match.group('plural'))

                try:
                    hint = match.group('hint') or u""
                except IndexError:
                    hint = u""
                    
                try:
                    group = _strip_quotes(match.group('group')) or DEFAULT_TRANSLATION_GROUP
                except IndexError:
                    group = DEFAULT_TRANSLATION_GROUP

                hint = _strip_quotes(hint)
                results.append((text, plural, hint, group))

        return results


def _scan_list(marshall, scan_id, filenames):
    # FIXME: Need to clean up the translations which aren't in use anymore

    for filename in filenames:
        # Redeploying to a new version can cause this
        if not os.path.exists(filename):
            continue

        with open(filename) as f:
            content = unicode(f.read(), settings.DEFAULT_CHARSET)

        results = parse_file(content, os.path.splitext(filename)[-1])

        for text, plural, hint, group in results:
            if not text:
                logger.warn("Empty translation discovered: '{}', '{}', '{}', '{}'".format(text, plural, hint, group))
                continue

            with transaction.atomic(xg=True):
                key = MasterTranslation.generate_key(text, hint, settings.LANGUAGE_CODE)

                try:
                    mt = MasterTranslation.objects.get(pk=key)
                except MasterTranslation.DoesNotExist:
                    mt = MasterTranslation(
                        pk=key, text=text, hint=hint, language_code=settings.LANGUAGE_CODE
                    )

                # By the very act of getting here, this is true
                mt.used_in_code_or_templates = True

                # If we last updated during this scan, then append, otherwise replace
                if mt.last_updated_by_scan_uuid == unicode(scan_id):
                    mt.used_by_groups_in_code_or_templates.add(group)
                else:
                    mt.used_by_groups_in_code_or_templates = { group }

                mt.last_updated_by_scan_uuid = scan_id
                mt.save()

    with transaction.atomic():
        marshall.refresh_from_db()
        marshall.files_left_to_process -= len(filenames)
        marshall.save()


def begin_scan(marshall):
    try:
        marshall.refresh_from_db()
    except ScanMarshall.DoesNotExist:
        logger.warn("Not starting scan as scanmarshall was missing")
        return

    scan_id = uuid.uuid4()

    files_to_scan = []

    def append_file(filename, files_to_scan):
        files_to_scan.append(filename)
        if len(files_to_scan) == 100:
            with transaction.atomic(xg=True):
                marshall.refresh_from_db()
                marshall.files_left_to_process += 100
                marshall.save()
                defer(_scan_list, marshall, scan_id, files_to_scan, _transactional=True)

            files_to_scan = []

    def walk_dir(root, dirs, files):
        for f in files:
            filename = os.path.normpath(os.path.join(root, f))
            if os.path.splitext(filename)[1] not in (".py", ".html"):
                continue

            append_file(filename, files_to_scan)

    for app in settings.INSTALLED_APPS:
        module_path = os.path.dirname(apps.get_app_config(app.split(".")[-1]).module.__file__)

        for root, dirs, files in os.walk(module_path, followlinks=True):
            walk_dir(root, dirs, files)

    #Scan the django directory
    for root, dirs, files in os.walk(os.path.dirname(django.__file__), followlinks=True):
        walk_dir(root, dirs, files)

    if files_to_scan:
        with transaction.atomic(xg=True):
            marshall.refresh_from_db()
            marshall.files_left_to_process += len(files_to_scan)
            marshall.save()
            defer(_scan_list, marshall, scan_id, files_to_scan, _transactional=True)
