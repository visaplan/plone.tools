# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79
"""\
functions: very simple functions for Plone
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (1,
           0,
           )
__version__ = '.'.join(map(str, VERSION))
__all__ = ['is_uid_shaped',
           'id_of',
           ]

# Standardmodule
from os.path import (
        splitext, split,
        )

UID_CHARS = frozenset(u'0123456789abcdef')
def is_uid_shaped(s, onerror='raise'):
    """
    Sieht der übergebene String aus wie eine UID?

    >>> is_uid_shaped('abc123')
    False
    >>> is_uid_shaped('0123456789abcdef0123456789abcdef')
    True
    >>> is_uid_shaped('0123456789ABCDEF0123456789ABCDEF')
    False

    """
    if isinstance(s, str):
        try:
            s = s.decode('ascii')
        except UnicodeDecodeError:
            return False
    elif isinstance(s, unicode):
        pass
    elif onerror == 'raise':
        raise ValueError('String expected: %(s)r'
                         % locals())
    else:
        return False
    return len(s) == 32 and UID_CHARS.issuperset(s)


def id_of(name):
    """
    Zur Verwendung in setup-Skripten etc.:
    erlaubt die Angabe einer (gf-verlinkbaren) Datei, von der für den
    auszuführenden Code nur die ID benötigt wird; z.B.:

    >>> id_of('skins/betonquali/bq_meinbetonquali.pt')
    'bq_meinbetonquali'
    >>> id_of('bq_nachrichten.pt')
    'bq_nachrichten'
    >>> id_of('fancy.xml.pt')
    'fancy.xml'
    """
    return splitext(split(name)[1])[0]


if __name__ == '__main__':
    import doctest
    doctest.testmod()
