# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _watch
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types

# Standard library:
from collections import defaultdict

__all__ = [
        'make_watcher_function',
        ]


def make_watcher_function(val, logger, **kwargs):
    """
    Erzeuge eine Funktion (für Debugging-Zwecke), die zwei Argumente
    entgegennimmt - einen Schlüssel (etwa eine UID) und einen String, z. B.
    einen Workflow-Zielstatus - und einen Wahrheitswert zurückgibt.
    Der aufrufende Code kann dann den Debugger aufrufen.

    Für Abkürzung der Doctests:
    >>> def mwf(val): return make_watcher_function(val, logger=None)

    Mögliche Werte:
    Ein 2-Tupel (key, val):
    >>> f = mwf(('abc123', 'restricted'))

    Eine Liste von 2-Tupeln:
    >>> f = mwf([('abc123', 'restricted'), ('cde465', 'restricted'))

    Dies kann auch abgekürzt werden (gleichwertige Darstellungen):
    >>> f = mwf([(('abc123', 'cde465a'),  'restricted')])
    >>> f = mwf( (('abc123', 'cde465a'),  'restricted') )
    >>> f = mwf([(('abc123', 'cde465a'), ['restricted'])])

    Als Dict (nah an der internen Darstellung; wiederum gleichwertig):
    >>> f = mwf({'abc123': 'restricted', 'cde465': 'restricted'})
    >>> f = mwf({('abc123', 'cde465'): ('restricted',)})

    Die zurückgegebene Funktion verwendet die Argumentnamen 'key' und 'val',
    die in der <msg> verwendet werden können; wenn ein Logger != None übergeben
    wurde, wird eine entsprechende Meldung protokolliert.
    """
    lists_for_uid = defaultdict(list)
    msg = kwargs.pop('msg', 'WATCHED CASE: %(key)r --> %(val)r')
    all_value = kwargs.pop('all_value', 'ALL')
    def checked_value(thelist):
        if (thelist != all_value and
            isinstance(thelist, six_string_types)
            ):
            return [thelist]
        if isinstance(thelist, tuple):
            return list(thelist)
        return thelist

    def nonstring_sequence(val):
        if isinstance(val, (list, tuple)):
            return val
        return [val]

    if isinstance(val, tuple):
        keys, thelist = tup
        for key in nonstring_sequence(keys):
            lists_for_uid[key] = checked_value(thelist)
    elif isinstance(val, list):
        for tup in val:
            keys, thelist = tup
            for key in nonstring_sequence(keys):
                lists_for_uid[key].extend(checked_value(thelist))
    elif isinstance(val, dict):
        for keys, thelist in val.items():
            for key in nonstring_sequence(keys):
                lists_for_uid[key] = checked_value(thelist)

    def watch(key, val):
        tmp = lists_for_uid[key]
        if tmp == all_value:
            if logger is not None:
                logger.info(msg, locals())
            return True
        elif isinstance(tmp, list):
            res = val in tmp
            if res and logger is not None:
                logger.info(msg, locals())
            return res
        else:
            return False

    return watch
