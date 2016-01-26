#SYSTEM
import fnmatch
import os
from optparse import make_option
import re
import sys
import csv
import json

#LIBRARIES
from django.conf import settings
from django.core.management.base import CommandError, BaseCommand
from django.utils.text import get_text_list, smart_split
from django.utils.translation import trim_whitespace

from fluent.utils import find_closest_supported_language


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
        r"""\s*\)"""
    ]

    NREGEXES = [
        r"""\b(_|npgettext_lazy|ngettext|npgettext|ungettext|ungettext_lazy)\(\s*"""
        r"""(?P<text>(?:".[^"]*?")|(?:'.[^']*?'))"""
        r"""(\s*,\s*(?P<plural>(?:".[^"]*?")|(?:'.[^']*?')))"""
        r"""(\s*,\s*(?P<count>(?:[^,)]*)))"""
        r"""(\s*,\s*(?P<hint>(?:".[^"]*?")|(?:'.[^']*?')))?"""
        r"""\s*\)"""
    ]

    TEMPLATE_VAR_RE = re.compile(r'{{\s*([_a-zA-Z]+)\s*}}')

    def _strip_quotes(text):
        if text[0] == text[-1] and text[0] in "'\"":
            return text[1:-1]
        return text

    def find_trans_nodes(tokens, output):
        start_tag = None
        buf = []
        plural_buf = []
        in_plural = False

        context = None
        group = DEFAULT_TRANSLATION_GROUP

        for i, (token_type, token) in enumerate(tokens):
            parts = list(smart_split(token))

            if "endblocktrans" in parts:
                buf_joined = "".join(buf)
                plural_buf_joined = "".join(plural_buf)
                if "trimmed" in list(smart_split(start_tag)):
                    buf_joined = buf_joined.strip()
                    plural_buf_joined = plural_buf_joined.strip()
                output.append((start_tag, buf_joined, plural_buf_joined, context, group))
                start_tag = None
                buf = []
                plural_buf = []
                in_plural = False
                context = ""

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
                    group = _strip_quotes(match.group('group')) if match.group('group') else DEFAULT_TRANSLATION_GROUP
                    hint = _strip_quotes(match.group('hint')) if match.group('hint') else None
                    output.append( (match.group(0), _strip_quotes(match.group('text')), "", hint, group) )

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
                    hint = match.group('hint')
                except IndexError:
                    hint = None

                if hint:
                    hint = _strip_quotes(hint)

                results.append((text, "", hint, DEFAULT_TRANSLATION_GROUP))

        for regex in NREGEXES:
            result = re.compile(regex).finditer(content)
            for match in result:
                text = _strip_quotes(match.group('text'))
                plural = _strip_quotes(match.group('plural'))

                try:
                    hint = match.group('hint')
                except IndexError:
                    hint = None

                if hint:
                    hint = _strip_quotes(hint)

                results.append((text, plural, hint, DEFAULT_TRANSLATION_GROUP))

        return results


def output_path():
    main_app_path = getattr(settings, 'PROJECT_ROOT', None) or os.environ["DJANGO_SETTINGS_MODULE"].split(".")[0]
    output_path = os.path.abspath(os.path.join(main_app_path, "fixtures"))
    return output_path


def output_file():
    return os.path.join(output_path(), "translations.json")


def make_messages(locale, verbosity, extensions, symlinks, ignore_patterns):
    def is_ignored(filename_):
        for pattern in ignore_patterns:
            if fnmatch.fnmatchcase(filename_, pattern):
                return True
            if os.path.splitext(filename_)[-1] not in extensions:
                return True
        return False

    def prepare_output_file():
        out_path = output_path()

        #We want to generate a fixture in {APP_WHERE_SETTINGS_RESIDES}/fixtures/translations.json
        if not os.path.exists(out_path):
            os.makedirs(out_path)

        #Delete any existing initial data from a previous run
        out_file = output_file()
        if os.path.exists(out_file):
            os.remove(out_file)

        return out_file

    files_to_scan = []

    import django
    from django.conf import settings
    from django.apps import apps

    for app in settings.INSTALLED_APPS:
        module_path = os.path.dirname(apps.get_app_config(app.split(".")[-1]).module.__file__)

        for root, dirs, files in os.walk(module_path, followlinks=symlinks):
            for f in files:
                filename = os.path.normpath(os.path.join(root, f))

                if is_ignored(filename):
                    continue

                files_to_scan.append(filename)

    #Scan the django directory
    for root, dirs, files in os.walk(os.path.dirname(django.__file__), followlinks=symlinks):
        for f in files:
            filename = os.path.normpath(os.path.join(root, f))

            if is_ignored(filename):
                continue

            files_to_scan.append(filename)


    files_to_scan.sort()

    out_file = prepare_output_file()

    json_content = []

    lookup = {}

    for filename in files_to_scan:
        results = parse_file(open(filename).read(), os.path.splitext(filename)[-1])

        for result in results:
            result = list(result)
            result[2] = result[2] or ""

            key = (result[0], result[2])

            if key in lookup:
                #Increase usage count?
                lookup[key]["count"] += 1
                lookup[key]["groups"] |= set([result[3]])
                continue

            json_content.append(
                {
                    "model": "fluent.MasterTranslation",
                    "pk": None, #We don't care
                    "fields": {
                        "text": result[0],
                        "plural_text": result[1] or "",
                        "hint": result[2] or "",
                        "language_code": locale,
                    }
                },
            )

            lookup[key] = {
                "count": 1,
                "groups": set([result[3]]),
                "plural_text": result[1] or ""
            }

    for instance in json_content:
        key = (instance["fields"]["text"], instance["fields"]["hint"])
        instance["fields"]["used_by_groups_in_templates"] = list(lookup[key]["groups"])

    open(out_file, "w").write(json.dumps(json_content, indent=4))
    return json_content

def write_pot_file(filename, translations):
    def write_translation(file_out, text, plural, hint):
        lines = [
            "#. {0}".format(hint),
            'msgid "{0}"'.format(text.replace('"', '\\"')),
        ]

        if plural:
            lines.append(
                'msgid_plural "{0}"'.format(plural.replace('"', '\\"'))
            )

            for i in xrange(6):
                lines.append('msgstr[{0}] ""'.format(i))
        else:
            lines.append('msgstr ""')

        lines.extend([
            "", "" #Spacing
        ])

        file_out.write("\n".join(lines))

    with open(filename, "w") as file_out:
        for translation in translations:
            write_translation(file_out,
                translation["fields"]['text'],
                translation["fields"]['plural_text'],
                translation["fields"]['hint']
            )

def write_csv_file(filename, translations):
    with open(filename, "w") as file_out:
        writer = csv.writer(file_out, delimiter=",", quotechar='"')

        headings1 = ["msgid",
            "msgid-plural",
            "#.",
            "msgstr-0"
            ] + [ "msgstr-%d" % (x + 1) for x in xrange(6)
        ]

        writer.writerow(headings1)

        writer.writerow([
            "String to be translated",
            "String to be translated in plural form (if any)",
            "Context",
            "Singular translation"
            ] + [ "Plural form %d translation" % (x + 1) for x in xrange(6) ]
        )

        for trans in translations:
            writer.writerow([
                trans["fields"]['text'],
                trans["fields"]['plural_text'],
                trans["fields"]['hint'] ] + [""] * (len(headings1) - 3))

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--extension',
            '-e',
            dest='extensions',
            default=['.dtml', '.html', '.py'],
            help='The file extension(s) to examine (default: ".dtml, .py", separate multiple extensions with commas, or use -e multiple times)',
            action='append'
        ),
        make_option(
            '--symlinks',
            '-s',
            action='store_true',
            dest='symlinks',
            default=False,
            help='Follows symlinks to directories when examining source code and templates for translation strings.'
        ),
        make_option(
            '--ignore',
            '-i',
            action='append',
            dest='ignore_patterns',
            default=[],
            metavar='PATTERN',
            help='Ignore files or directories matching this glob-style pattern. Use multiple times to ignore more.'
        ),
        make_option(
            '--no-default-ignore',
            action='store_false',
            dest='use_default_ignore_patterns',
            default=True,
            help="Don't ignore the common glob-style patterns 'CVS', '.*' and '*~'."
        ),
        make_option(
            '--export-pot',
            dest='pot_filename',
            help="Export the translations to the specified POT file"
        ),

        make_option(
            '--export-csv',
            dest='csv_filename',
            help="Export the translations to the specified CSV file"
        ),

        make_option(
            '--group',
            dest='group',
            help="Limit exporting to this group"
        )
    )
    help = "Runs over the entire source tree of the current directory and pulls out all strings and chunks marked for translation. It creates one file for inline strings and one for chunks - they are both python format."

    requires_model_validation = False
    can_import_settings = True
    leave_locale_alone = True

    def handle(self, *args, **options):
        if len(args) != 0:
            raise CommandError("Command doesn't accept any arguments")

        locale = getattr(settings, "LANGUAGE_CODE", "en")
        locale = find_closest_supported_language(locale)


        verbosity = int(options.get('verbosity'))
        extensions = options.get('extensions')
        symlinks = options.get('symlinks')
        ignore_patterns = options.get('ignore_patterns')
        if options.get('use_default_ignore_patterns'):
            ignore_patterns += ['CVS', '.*', '*~']

        # ignore contents of test directories, common libraries and source control
        ignore_patterns += ['*/tests/*', '*tests.py']
        ignore_patterns += ['django/*', 'djangoappengine/*', 'djangotoolbox/*', 'mapreduce/*']
        ignore_patterns += ['.svn/*', '.git/*']
        ignore_patterns += ['*.pyc', '*.pyo', '*.pyd']

        if hasattr(settings, 'FLUENT_EXTRA_IGNORE_PATTERNS'):
            ignore_patterns += settings.FLUENT_EXTRA_IGNORE_PATTERNS

        ignore_patterns = list(set(ignore_patterns))

        if verbosity > 1:
            sys.stdout.write('examining files with the extensions: %s\n' % get_text_list(list(extensions), 'and'))

        trans = make_messages(locale, verbosity, extensions, symlinks, ignore_patterns)

        if options.get("group"):
            group = options.get("group")
            trans = [ x for x in trans if group in x["fields"]['used_by_groups_in_templates'] ]

        if options.get('pot_filename'):
            write_pot_file(options['pot_filename'], trans)
        if options.get('csv_filename'):
            write_csv_file(options['csv_filename'], trans)
