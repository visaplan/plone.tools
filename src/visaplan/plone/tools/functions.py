# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79
"""\
functions: very simple functions for Plone
"""

# Python compatibility:
from __future__ import absolute_import

from six import text_type as six_text_type
from six.moves import map

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

# Standard library:
from os.path import split, splitext

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
    visaplan.plone.tools.forms.uid_or_number.

    ACHTUNG:
    Diese Funktion reagiert qua Vorgabe ungnädig auf unzulässige Werte:
    >>> is_uid_shaped(None)
    Traceback (most recent call last):
      ...
    ValueError: String expected: None
    >>> is_uid_shaped(42, onerror="raise")
    Traceback (most recent call last):
      ...
    ValueError: String expected: 42
    
    Durch Angabe eines anderen Werts als "raise" für die `onerror`-Option
    läßt sich dies beheben; *welcher* Wert dabei verwendet wird, wird aktuell
    noch ignoriert:
    >>> is_uid_shaped(None, '')
    False
    >>> is_uid_shaped(None, False)
    False

    Die Angabe "falschiger" Werte wird in diesem Fall dringend empfohlen;
    diese könnten zukünftig auch als Rückgabewert für diesen Fall verwendet
    werden.
    Wie "wahre" Strings außer 'raise' und sonstige "wahre" Werte
    zukünftig verstanden werden, ist undefiniert!

    Finally, a few basic assumptions of the function:
    >>> isinstance(b'123', bytes)
    True
    >>> isinstance(b'123', six_text_type)
    False
    >>> isinstance(u'123', six_text_type)
    True
    >>> isinstance(u'123', bytes)
    False

    The following test, however:
    >>> isinstance('123', str)
    True

    doesn't tell about the existence of the .decode method consistently in
    Python 2 and Python 3.
    """
    if isinstance(s, six_text_type):
        pass
    elif isinstance(s, bytes):
        try:
            s = s.decode('ascii')
        except UnicodeDecodeError:
            return False
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

    Es gibt allerdings einen Unterschied in der Behandlung von Fehlern,
    der dabei zu beachten ist:

    >>> looksLikeAUID(None)
    False
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
    # Standard library:
    import doctest
    doctest.testmod()
