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
           # ---------------- [ aus Products.unitracc.tools.misc ... [
           'looksLikeAUID',  # weniger empfohlen ...
           # ---------------- ] ... aus Products.unitracc.tools.misc ]
           ]

# Standardmodule
from os.path import (
        splitext, split,
        )

UIDCHARS_UNICODE = frozenset(u'0123456789abcdef')
def is_uid_shaped(s, onerror='raise'):
    """
    Sieht der übergebene String aus wie eine UID?

    >>> is_uid_shaped('abc123')
    False
    >>> is_uid_shaped('0123456789abcdef0123456789abcdef')
    True
    >>> is_uid_shaped('0123456789ABCDEF0123456789ABCDEF')
    False

    Verwendet z. B. zum Erzeugen des 'uid'-Werts von
    visaplan.plone.tools.forms.uid_or_number
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
    return len(s) == 32 and UIDCHARS_UNICODE.issuperset(s)


# --------------------------- [ aus Products.unitracc.tools.misc ... [
UIDCHARS_BYTES = set('abcdef0123456789')
def looksLikeAUID(uid):
    """
    Sieht der übergebene String wie eine UID aus?

    >>> looksLikeAUID('abcdabcdabcdabcdabcdabcdabcdabcd')
    True
    >>> looksLikeAUID('abcdabcdabcdabcdabcdabcdabcdabc')
    False
    >>> looksLikeAUID(u'abcdabcdabcdabcdabcdabcdabcdabcd')
    True
    >>> looksLikeAUID(u'ä')
    False
    >>> looksLikeAUID('ABCDABCDABCDABCDABCDABCDABCDABCD')
    False
    >>> looksLikeAUID(42)
    False

    Die vorliegende Funktion "fällt auf Listen herein":
    >>> sillyuid = list('abcd'*8)
    >>> sillyuid[:8]
    ['a', 'b', 'c', 'd', 'a', 'b', 'c', 'd']
    >>> looksLikeAUID(sillyuid)
    True

    Sie wird hier daher vorwiegend aus historischen Gründen erhalten;
    die Umstellung auf is_uid_shaped (siehe oben) wird empfohlen.
    """
    try:
        if len(uid) != 32:
            return False
    except TypeError:
        return False
    else:
        return set(uid).issubset(UIDCHARS_BYTES)
# --------------------------- ] ... aus Products.unitracc.tools.misc ]


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
