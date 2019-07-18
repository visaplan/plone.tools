# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 si et textwidth=72 cc=+8
"""
visaplan.plone.tools.log - Helferlein für Entwicklung und Debugging

Autor: Tobias Herp
"""

# Standardmodule:
import logging
from os import linesep, getpid
from fcntl import lockf, LOCK_EX, LOCK_UN
from time import strftime
from contextlib import contextmanager
from functools import wraps
from pprint import pformat

# Plone/Zope:
from Globals import DevelopmentMode

# Unitracc-Tools:
from visaplan.plone.tools.cfg import get_debug_active, split_filename
from visaplan.tools.coding import safe_decode, safe_encode
from visaplan.tools.debug import arginfo, pretty_funcname


__all__ = ['getLogSupport',
           'make_textlogger',
           ]

TIMEFORMAT_VERBOSE = u'%Y-%m-%d %T %Z (%A) '
TIMEFORMAT_LASTCHARS = u' |-\t'
_DEVMODE_STRING = str(DevelopmentMode)

def getLogSupport(name=None,
                  fn=None,
                  defaultFromDevMode=False,
                  default=None,
                  **kwargs):
    """
    Verwendung:

      from ...tools.log import getLogSupport
      logger, debug_active, DEBUG = getLogSupport(fn=__file__)
    oder
      logger, debug_active, DEBUG = getLogSupport()

    Standardmäßig Debugging aktivieren:
      logger, debug_active, DEBUG = getLogSupport(..., default='True')

    ... oder nur bei Entwicklungsmodus:
      logger, debug_active, DEBUG = getLogSupport(..., defaultFromDevMode=1)
    """
    if 'stack_limit' not in kwargs:
        kwargs['stack_limit'] = 3
    name, label = split_filename(fn, name,  # stack_limit=stack_limit,
                                 **kwargs)
    logger = logging.getLogger(label)
    if default is None:
        default = defaultFromDevMode and _DEVMODE_STRING or 'False'
    elif not isinstance(default, str):
        raise ValueError('default must be a string! (%(default)r)'
                         % locals())
    tmp = get_debug_active(name,
                           default)
    if DevelopmentMode:
        debug_active = tmp
    else:
        # Debugging auch in Produktionsmodus:
        # Wert auf 2 (oder noch höher) setzen
        debug_active = tmp > 1
    if debug_active:
        method = logger.info
        method('*** Debugging AKTIV ***')
    else:
        method = logger.debug
    return (logger,
            debug_active,
            method,
            )  # ----------------------------------- ... getLogSupport

@contextmanager
def locked_open(filename, mode='r'):
    """
    Öffnet die übergebene Datei und reserviert sie für exklusiven Zugriff;
    zu verwenden wie die eingebaute open-Funktion
    """
    # von --> https://gist.github.com/lonetwin/7b4ccc93241958ff6967
    with open(filename, mode) as fd:
        lockf(fd, LOCK_EX)
        yield fd
        lockf(fd, LOCK_UN)


def make_textlogger(fn, sorting_filter=None, divide=None, lock=None,
                    time_format=TIMEFORMAT_VERBOSE,
                    debug=False):
    """
    Erzeuge eine Funktion, die (mit <lock>) eine Datei zum exklusiven Zugriff
    reserviert, einmal schreibt und dann nach Freigabe der Datei wieder
    zurückkehrt.

    fn -- der Dateiname, z. B. '.../users.txt'
    sorting_filter -- Eine Funktion, die die Schlüssel eines übergebenen
                      Python-Dicts sortiert und ggf. filtert.
    divide -- eine Trennzeile
    lock -- soll die Datei jeweils zum exklusiven Zugriff gesperrt
            werden? (None --> Default verwenden)
    time_format -- Vorgabe: '%Y-%m-%d %T %Z (%A) '
    debug -- wenn True, werden die internen Aufrufe von make_text
             protokolliert

    Es wird jedenfalls ein Logger erzeugt, der über den Vorgang
    informiert und (für den Fall, daß die Dateiangabe leer ist) als
    Fallback-Option fungiert.
    """
    logger = getLogSupport(stack_limit=3)[0]
    if sorting_filter is None:
        sorting_filter = dict.items
    if divide is None:
        divide = 79 * u'-'
    elif not divide:
        divide = None
    else:
        divide = safe_decode(divide.strip())
    if not time_format:
        time_format = TIMEFORMAT_VERBOSE
    else:
        time_format = safe_decode(time_format)
    if not time_format[-1] in TIMEFORMAT_LASTCHARS:
        timeformat += TIMEFORMAT_LASTCHARS[0]
    PROTOMASK = u'%%-%ds%%s'

    def fallback(txt, **kwargs):
        """
        Verwende die allgemeine Logging-Unterstützung
        """
        items = sorting_filter(kwargs)
        logger.info(' '.join((txt,
                              '; '.join(['%s=%s' % tup
                                         for tup in items])
                              )))

    def make_text(txt, **kwargs):
        """
        Erzeuge einen mehrzeiligen Text (UTF-8-codiert).
        Eingabeargumente werden mit safe_decode zu Unicode decodiert.
        """
        items = sorting_filter(kwargs)
        maxl = max(map(len, [t[0] for t in items])) + 2
        mask = PROTOMASK % maxl
        liz = [u'']
        if divide is not None:
            liz.append(divide)
        liz.append( strftime(time_format)+safe_decode(txt)+u':')
        liz_u = []
        for key, val in items:
            if isinstance(val, basestring):
                liz_u.append((safe_decode(key)+u':', safe_decode(val)))
            else:
                liz_u.append((safe_decode(key)+u':', val))
        liz.extend([mask % tup
                    for tup in liz_u
                    ])
        liz.append(u'')
        return safe_encode(u'\n'.join(liz))

    def log_call_and_result(func):
        DEBUG = logger.info
        _funcname = pretty_funcname(func)
        @wraps(func)
        def inner(*args, **kwargs):
            DEBUG('%s(%s) ...', _funcname, arginfo(*args, **kwargs))
            _res = func(*args, **kwargs)
            if not _res:
                DEBUG('%s(...) --> %r', _funcname, _res)
            elif isinstance(_res, tuple):
                DEBUG('%s(...) --> %s values:', _funcname, len(_res))
                for val in _res:
                    DEBUG(pformat(val))
            else:
                DEBUG('%s(...) -->\n%s',
                      _funcname,
                      pformat(_res))
            return _res

        inner.__name__ = _funcname
        return inner

    if debug:
        make_text = log_call_and_result(make_text)

    if lock:
        file_context = locked_open
    else:
        file_context = open

    def text_logger(txt, **kwargs):
        cooked = make_text(txt, **kwargs)
        with file_context(fn, 'a') as fd:
            fd.write(cooked)

    if fn:
        # OK, Dateiname angegeben; "locking logger" erzeugen:
        if lock:
            logger.info('Creating locking logger for %(fn)r', locals())
        else:
            logger.info('Creating text logger for %(fn)r', locals())
        return text_logger

    logger.info('Creating default logger!')
    return fallback


if __name__ == '__main__':
    import doctest
    doctest.testmod()
