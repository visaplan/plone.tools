# -*- coding: utf-8 -*- vim: tw=79 cc=+1 sw=4 sts=4 et si
"""
visaplan.plone.tools: attools: Archetypes-related tools (_at4)
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types
from six import text_type as six_text_type

# visaplan:
from visaplan.tools.coding import safe_decode
from visaplan.tools.html import from_plain_text

# Local imports:
from ._at3 import getter_name


def get_first_text_as_html(context, *fieldnames, **kwargs):
    """
    Get the first (existing) text field, as HTML

    Keyword options:

    - ignore_empty (default: True) --
        If a field exists but is empty (or contains a non-string value),
        try the next one;
        with ignore_empty=False,
        any value of the first existing field would be used.

    - decode (default: visaplan.plone.coding.safe_decode) --
        a function to decode a bytes string to unicode.
        Specify a falsy value to suppress decoding.

    If the field contains text/plain (i.e., the content doesn't start with
    '<'), it is converted to HTML, using a simple function, which

    - creates paragraphs for each line (or sequence of lines), delimited by
      empty lines,
    - unless starting with a &bull; or dash; in this case, it is considered
      part of a list.

    See visaplan.tools.html.from_plain_text for details.
    """
    ignore_empty = kwargs.pop('ignore_empty', 1)
    if 'decode' not in kwargs:
        decode = safe_decode
    else:
        decode = kwargs.pop('decode')
        if not decode:
            decode = None

    if 'schema' in kwargs:
        schema = kwargs.pop('schema')
    elif fieldnames and not isinstance(fieldnames[0], six_string_types):
        fieldnames = list(fieldnames)
        schema = fieldnames.pop(0)
    else:
        schema = None
    if schema is not None:
        raise ValueError('Sorry; using a dedicated schema here (%(schema)r)'
                         'is not yet supported'
                         % locals())

    if kwargs:
        raise TypeError('Unsupported keyword option(s): %s' % (
                        ', '.join(sorted(set(kwargs))),
                        ))
    if not fieldnames:
        fieldnames = ['description', 'text']
    for fieldname in fieldnames:
        try:
            val = getattr(context, fieldname)
        except AttributeError:
            gname = getter_name(fieldname)
            try:
                getter = getattr(context, gname)
            except AttributeError:
                continue
            else:
                val = getter()

        if not isinstance(val, six_string_types):
            if ignore_empty:
                continue
            else:
                return fieldname, ''
        if decode is not None and not isinstance(val, six_text_type):
            val = decode(val)
        if not val.startswith(u'<'):
            val = val.strip()
        if not val and ignore_empty:
            continue
        if not val.startswith(u'<'):
            val = from_plain_text(val)
        return fieldname, val
    return None, ''
