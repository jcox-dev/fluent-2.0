from __future__ import absolute_import

from django import template
from django.templatetags.i18n import do_translate, do_block_translate, TranslateNode
from django.utils.translation import get_language, trim_whitespace
from django.template.defaultfilters import force_escape, safe as safe_filter
from django.utils.html import conditional_escape

register = template.Library()


class EscapedTranslateNode(TranslateNode):
    """ Subclass of the Django TranslateNode, but which escapes the output. """

    def render(self, context):
        # Escape the output of the `trans` tag, if it hasn't been escaped already
        return conditional_escape(
            super(EscapedTranslateNode, self).render(context)
        )


@register.tag("trans")
def trans_override(parser, token):
    """
        Wraps around Django's trans tag, but allows for 'group "Thing"' to be
        specified (group is only used for exporting) not for translation.
    """
    contents = token.split_contents()

    escape = True
    if "noescape" in contents:
        contents.remove("noescape")
        escape = False

    if "group" in contents:
        #Remove the group tag from the token
        idx = contents.index("group")
        group = contents[idx + 1]
        contents.remove("group")
        contents.remove(group)

    token.contents = " ".join(contents)

    result = do_translate(parser, token)

    if escape:
        # If the 'noescape' option has NOT been passed, then we treat both the default text and the
        # translated text as not HTML safe.
        return EscapedTranslateNode(
            result.filter_expression,
            result.noop,
            result.asvar,
            result.message_context
        )
    else:
        # If the 'noescape' option has been passed to the tag then we need to tell Django not to
        # escape the result. If the result is just the default text from the string literal inside
        # the `{% trans %}` tag instance then Django will treat it as safe anyway. But if the
        # result has come from a translation then Django will not treat it as safe, so we need to
        # add the |safe filter to tell Django not to escape it.
        result.filter_expression.filters.append((safe_filter, []))
        return result


def _trim_text(tokens):
    for i, token in enumerate(tokens):
        token.contents = trim_whitespace(token.contents)
        if i == 0 and token.contents[0] == " ": #  first tag
            token.contents = token.contents[1:]
        elif i == len(tokens) - 1 and token.contents[-1] == " ":  # last tag
            token.contents = token.contents[:-1]


def _escape_text(tokens):
    for token in tokens:
        token.contents = force_escape(token.contents)


@register.tag("blocktrans")
def blocktrans_override(parser, token):
    """
        Wraps around Django's trans tag, but allows for 'group "Thing"' to be
        specified (group is only used for exporting) not for translation.
    """
    contents = token.split_contents()
    trimmed = ("trimmed" in contents)

    escape = True
    if "noescape" in contents:
        contents.remove("noescape")
        escape = False

    if "group" in contents:
        #Remove the group tag from the token
        idx = contents.index("group")
        group = contents[idx + 1]
        contents.remove("group")
        contents.remove(group)

    token.contents = " ".join(contents)

    node = do_block_translate(parser, token)
    if trimmed:
        _trim_text(node.singular)
        if node.plural:
            _trim_text(node.plural)

    if escape:
        _escape_text(node.singular)
        if node.plural:
            _escape_text(node.plural)

    return node


@register.filter
def translate(value, language_code=None):
    language_code = language_code or get_language()
    return value.translation(language_code)
