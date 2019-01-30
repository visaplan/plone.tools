# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79
"""
Mock-Klassen für Doctests
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           4,  # MockBrowser, MockContext
           1,  # MockRequest(actual_url=...)
           )
__version__ = '.'.join(map(str, VERSION))
__all__ = ('MockPortal',
           'MockRequest',
           'MockBrain',
           'MockProfile',
           'MockLogger',
           'MockBrowser',
           )


class MockPortal:
    """
    Aus forms-Modul extrahiert (dort nicht mehr benötigt).
    """
    def absolute_url(self):
        return 'http://test.me'


class MockRequest(dict):
    def __init__(self, referer=None, **kwargs):
        self['HTTP_REFERER'] = referer
        self['ACTUAL_URL'] = kwargs.pop('actual_url', referer)
        self.form = dict(kwargs)


class MockBrain(dict):
    """
    Brain-Objekte haben folgende Methoden:
    - has_key bzw. __contains__

    Der Zugriff funktioniert aber nicht mit b.get(key),
    sondern nur mit getattr(b, key) ...
    """

    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        for (k, v) in kwargs.items():
            setattr(self, k, v)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(['%s=%r' % (key, self[key])
                                      for key in sorted(self.keys())
                                      ]))


class MockProfile:
    """
    Benutzerprofil;
    aus ..browser.registration.utils:
    """
    def UID(self):
        return 'abc123'


class MockLogger(list):
    """
    für Testzwecke; schreibt 2-Tupel in eine Liste und verhält sich ansonsten als solche.

    >>> logger = MockLogger()
    >>> logger.info('Eine Info (%(eins)s)', {'eins': 'zwei'})
    >>> logger.error('%d Fehler', 3)
    >>> list(logger)
    [('INFO', 'Eine Info (zwei)'), ('ERROR', '3 Fehler')]
    """
    def _cook(self, txt, *args):
        if args:
            if not args[1:] and isinstance(args[0], dict):
                return txt % args[0]
            return txt % args
        else:
            return txt

    def error(self, txt, *args):
        self.append(('ERROR', self._cook(txt, *args)))

    def info(self, txt, *args):
        self.append(('INFO', self._cook(txt, *args)))


class MockContext:
    # siehe auch MockProfile
    def UID(self):
        return 'MockUID_' * 4


class MockBrowser:
    """
    Für Doctests von Browsermethoden
    """
    context = MockContext()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
