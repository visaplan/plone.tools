# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Methoden zum Erzeugen von Indexfeldern;
etwas weniger "prominent" als die Funktionen aus .context
"""

from plone.i18n.normalizer.base import mapUnicode
from visaplan.tools.coding import safe_decode

mapping = {
138: 's',  140: 'O',  142: 'z',  154: 's',  156: 'o',  158: 'z',  159: 'Y',
192: 'A',  193: 'A',  194: 'A',  195: 'a',  196: 'A',  197: 'Aa', 198: 'E',
199: 'C',  200: 'E',  201: 'E',  202: 'E',  203: 'E',  204: 'I',  205: 'I',
206: 'I',  207: 'I',  208: 'Th', 209: 'N',  210: 'O',  211: 'O',  212: 'O',
213: 'O',  214: 'O',  215: 'x',  216: 'O',  217: 'U',  218: 'U',  219: 'U',
220: 'U',  222: 'th', 221: 'Y',  223: 's',  224: 'a',  225: 'a',  226: 'a',
227: 'a',  228: 'a',  229: 'aa', 230: 'a',  231: 'c',  232: 'e',  233: 'e',
234: 'e',  235: 'e',  236: 'i',  237: 'i',  238: 'i',  239: 'i',  240: 'th',
241: 'n',  242: 'o',  243: 'o',  244: 'o',  245: 'o',  246: 'o',  248: 'o',
249: 'u',  250: 'u',  251: 'u',  252: 'u',  253: 'y',  254: 'Th', 255: 'y'}

def getSortableTitle(context):
    """
    Normalisiere den Titel des aufrufenden Objekts;
    Ersatz für die Skin-Layer-Methode getSortableTitle.

    >>> getSortableTitle(MockContext(u'Ärmel'))
    'armel'
    """
    txt = context.Title().strip().lower()
    txt = safe_decode(txt)
    return mapUnicode(txt, mapping)


if __name__ == '__main__':
    class MockContext(object):
        def __init__(self, title):
            self.title = title
        def Title(self):
            return self.title

    import doctest
    doctest.testmod()
