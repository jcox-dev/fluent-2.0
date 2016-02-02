from __future__ import absolute_import

from django import template
from django.templatetags.i18n import do_translate, do_block_translate
from django.utils.translation import get_language, trim_whitespace


register = template.Library()


@register.tag("trans")
def trans_override(parser, token):
    """
        Wraps around Django's trans tag, but allows for 'group "Thing"'
        to be specified
    """
    contents = token.split_contents()
    if "group" in contents:
        #Remove the group tag from the token
        idx = contents.index("group")
        group = contents[idx + 1]
        contents.remove("group")
        contents.remove(group)
        token.contents = " ".join(contents)

    return do_translate(parser, token)


def _trim_text(tokens):
    for i, token in enumerate(tokens):
        token.contents = trim_whitespace(token.contents)
        if i == 0 and token.contents[0] == " ": #  first tag
            token.contents = token.contents[1:]
        elif i == len(tokens) - 1 and token.contents[-1] == " ":  # last tag
            token.contents = token.contents[:-1]


@register.tag("blocktrans")
def blocktrans_override(parser, token):
    """
        Wraps around Django's trans tag, but allows for 'group "Thing"'
        to be specified
    """
    contents = token.split_contents()
    trimmed = ("trimmed" in contents)
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
    return node


@register.filter
def translate(value, language_code=None):
    language_code = language_code or get_language()
    return value.translation(language_code)
