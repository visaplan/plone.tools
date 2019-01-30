# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Tools for "brains"
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           6,  # aufgeräumt
           )
__version__ = '.'.join(map(str, VERSION))


# Standardmodule
from collections import defaultdict

# Unitracc-Restrukturierung
from visaplan.tools.minifuncs import NoneOrString

__all__ = [
           'make_collector',
           ]


def make_collector(use, all=None, any=None, separator=" ", empty=None):
    """
    Gib eine Funktion zurück, die aus einem Brain-Objekt die angegebenen
    Attribute extrahiert und als String (Normalfall)
    oder als Liste (separator == None) zurückgibt.
    Argumente:

    use -- geordnete Sequenz der Attributnamen.
           Jedes Element der Sequenz darf ein 2-Tupel sein;
           in diesem Fall ist der erste Teil der Attributname, der zweite
           eine Transformationsfunktion, der der Wert übergeben wird.
    all -- wenn übergeben, müssen alle hier angegebenen Attribute einen
           nicht-leeren Wert haben; andernfalls wird <empty> zurückgegeben
    any -- komplementär zu <all>: wenn ein beliebiges der hier angegebenen
           Attribute einen nicht-leeren Wert hat ...
    separator -- Wenn None, wird ggf. eine Liste zurückgegeben; wenn das all-
                 oder any-Kriterium nicht erfüllt ist, eine leere Liste
    empty -- der Wert, wenn das all- oder any-Kriterium nicht erfüllt ist.
             Wird ignoriert, wenn <separator> None ist (was bedeutet, daß eine
             Liste zurückgegeben wird; in diesem Fall kommt eine leere Liste
             zurück).

    Die Angaben für all bzw. any sollten Untermengen von use sein - ansonsten
    wird hier nicht versprochen, daß sie korrekt verarbeitet werden!

    Derzeit kann nur *entweder* all *oder* any angegeben werden;
    für genau ein enthaltenes Element ist die Bedeutung allerdings identisch.

    >>> from sys import path
    >>> from os.path import dirname
    >>> path.insert(0, dirname(__file__))
    >>> from mock import MockBrain
    >>> caesar=MockBrain(getAcademicTitle='Dr.', getFirstname='Hase',
    ...                  getLastname='Caesar')
    >>> use=sorted(caesar.keys())
    >>> f_any=make_collector(use=use)
    >>> otto=MockBrain(getFirstname='Otto')

    Die Funktion f_any gibt nun immer einen String zurück, wenn das übergebene
    dict für mindestens eines dieser Attribute einen Wert hat.

    >>> f_any(caesar)
    'Dr. Hase Caesar'
    >>> f_any(otto)
    'Otto'

    Um nur dann etwas auszugeben, wenn ein Nachname vorhanden ist
    (ein einzelner Wert darf als String übergeben werden):

    >>> f_all=make_collector(use=use, all='getLastname')
    >>> f_all(caesar)
    'Dr. Hase Caesar'
    >>> f_all(otto)

    Achtung:
    Die Collectorfunktionen können (und sollten möglichst) schon beim Laden des
    Moduls erzeugt werden; es sind nämlich noch nicht alle möglichen Varianten
    implementiert ...
    """

    # ----------------------- [ make_collector: Argumente prüfen ... [
    def make_set(sos):
        """
        sos -- string or sequence

        Gib ein Set zurück.
        Wenn ein String übergeben wurde, füge ihn als Ganzes hinzu:

        >>> make_set('getFirstname')
        set(['getFirstname'])

        Sonstige Sequenzen und Sets werden normal verarbeitet:

        >>> make_set(['getFirstname', 'getLastname'])
        set(['getFirstname', 'getLastname'])
        """
        if isinstance(sos, basestring):
            return set([sos])
        else:
            return set(sos)

    assert use
    if all is None:
        if any is None:
            any = make_set(use)
        else:
            any = make_set(any)
    else:
        assert any is None, ('Es kann nur *entweder* all (%(all)r) *oder*'
                             ' any (%(any)r) angegeben werden!'
                             % locals())
        all = make_set(all)
    if separator is None:
        assert empty is None, 'empty wird nicht verwendet!'
    has_tuples = 0
    for key in use:
        if isinstance(key, tuple):
            has_tuples = 1
            break
    if has_tuples:
        use2 = []
        for key in use:
            if isinstance(key, tuple):
                use2.append(key)
            else:
                use2.append((key, None))
        use = use2
    # ----------------------- ] ... make_collector: Argumente prüfen ]

    # --------------------------------- [ einfache Werte, String ... [
    def collect_any(o):
        """
        any angegeben, ggf. empty
        """
        found = set()
        res = []
        allnames = dir(o)
        for key in use:
            if o.has_key(key):
                val = getattr(o, key, None)
                if val:
                    res.append(val)
                    found.add(key)
        if res and found.intersection(any):
            return separator.join(res)
        else:
            return empty

    def collect_all(o):
        """
        all angegeben, ggf. empty
        """
        res = []
        allnames = dir(o)
        for key in use:
            if key in o:
                val = getattr(o, key, None)
                if val:
                    res.append(val)
                    continue
            if key in all:
                return empty
        if res:
            return separator.join(res)
        else:
            return empty
    # --------------------------------- ] ... einfache Werte, String ]

    # ---------------------------- [ einzelne Funktionen, String ... [
    def collect_any_funcs(o):
        """
        any angegeben, ggf. empty
        """
        found = set()
        res = []
        allnames = dir(o)
        for (key, func) in use:
            if key in o:
                val = getattr(o, key, None)
                if func is not None:
                    val = func(val)
                if val:
                    res.append(val)
                    found.add(key)
        if res and found.intersection(any):
            return separator.join(res)
        else:
            return empty

    def collect_all_funcs(o):
        """
        all angegeben, ggf. empty
        """
        res = []
        allnames = dir(o)
        for (key, func) in use:
            if key in o:
                val = getattr(o, key, None)
                if func is not None:
                    val = func(val)
                if val:
                    res.append(val)
                    continue
            if key in all:
                return empty
        if res:
            return separator.join(res)
        else:
            return empty
    # ---------------------------- ] ... einzelne Funktionen, String ]

    # ---------------------------------- [ einfache Werte, Liste ... [
    def collect_any_list(o):
        """
        any angegeben, ggf. []
        """
        found = set()
        res = []
        allnames = dir(o)
        for key in use:
            if key in o:
                val = getattr(o, key, None)
                if val:
                    res.append(val)
                    found.add(key)
        if res and found.intersection(any):
            return separator.join(res)
        else:
            return []

    def collect_all_list(o):
        """
        all angegeben, ggf. []
        """
        res = []
        allnames = dir(o)
        for key in use:
            if key in o:
                val = getattr(o, key, None)
                if val:
                    res.append(val)
                    continue
            if key in all:
                return []
        if res:
            return separator.join(res)
        else:
            return []
    # ---------------------------------- ] ... einfache Werte, Liste ]

    if separator is not None:
        if any:
            if has_tuples:
                return collect_any_funcs
            else:
                return collect_any
        else:
            assert all
            if has_tuples:
                return collect_all_funcs
            else:
                return collect_all
    ## -------------------------------------------- ... make_collector


if __name__ == '__main__':
    import doctest
    doctest.testmod()
