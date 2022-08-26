# -*- coding: utf-8 -*- vim: tw=79 cc=+1 sw=4 sts=4 et si
"""
visaplan.plone.tools: attools: Archetypes-related tools (_at4)
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types
from six import text_type as six_text_type

# 3rd party:
from bs4 import BeautifulSoup

# visaplan:
from visaplan.tools.coding import safe_decode
from visaplan.tools.html import from_plain_text

# Local imports:
from ._at3 import getter_name
from ._at5 import is_nonempty_string


def generate_all_texts(context, *fieldnames, **kwargs):
    """
    Generate all (existing) text fields as (fieldname, value) tuples

    Keyword options:

    - ignore_empty (default: True) --
        If a field exists but is empty (or contains a non-string value),
        try the next one;
        with ignore_empty=False,
        any value of the first existing field would be used.

    - decode (default: visaplan.plone.coding.safe_decode) --
        a function to decode a bytes string to unicode.
        Specify a falsy value to supporess decoding.

    If the field contains text/html (i.e., the content starts with
    '<'), it is converted to text/plain.
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
        schema = context.Schema()
    if schema is not None:
        raise ValueError('Sorry; using a dedicated schema here (%(schema)r)'
                         'is not yet supported'
                         % locals())

    if kwargs:
        raise TypeError('Unsupported keyword option(s): %s' % (
                        ', '.join(sorted(set(kwargs))),
                        ))
    if not fieldnames:
        fieldnames = [
                'title',
                'subject',
                'description',
                'text',
                ]
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

        if isinstance(val, (list, tuple)):
            val = u' '.join([
                safe_decode(chunk)
                for chunk in val
                if is_nonempty_string(chunk)
                ])
        elif not isinstance(val, six_string_types):
            if ignore_empty:
                continue
            else:
                yield fieldname, ''
        if decode is not None and not isinstance(val, six_text_type):
            val = decode(val)
        if not val.startswith(u'<'):
            val = val.strip()
        if not val and ignore_empty:
            continue
        if val.startswith(u'<'):
            soup = BeautifulSoup(val, 'lxml')
            val = soup.text
        yield fieldname, val


def get_all_texts(context, *fieldnames, **kwargs):
    """
    Get all (existing) texts fields, joined to one unicode string
    """
    res = []
    for fieldname, value in generate_all_texts(context,
                                               *fieldnames, **kwargs):
        if value:
            res.append(value)
    return u' '.join(res)
