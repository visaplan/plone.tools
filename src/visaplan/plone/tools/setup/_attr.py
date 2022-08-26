# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _attr
"""

# Python compatibility:
from __future__ import absolute_import

# visaplan:
from visaplan.tools.classes import CheckedSetterDict, GetterDict, Proxy

__all__ = [
        'make_attribute_setter',
        ]


def make_attribute_setter(logger, setters=None, dryrun=0):
    """
    Gib eine Funktion zurück, die Attribute mit der jeweils passenden Methode
    setzt.

    ACHTUNG: Es wird bisher keinerlei Rückgriff auf das Schema genommen;
             für HTML-Felder z. B. ist das mutmaßlich noch nicht gut genug!
    """
    setters_map = CheckedSetterDict()
    getters_map = GetterDict()
    if setters is not None:
        # spezielle zu verwendende Werte:
        setters_map.update(setters)
    stem = '%(o)r: '

    def make_info(x):
        if x is None:
            return ' using setattr'
        return ' using setter %(x)r' % locals()

    info_dict = Proxy(make_info)

    def set_attribute(o, key, newvals, oldvals=None, dryrun=dryrun):
        """
        Setze das übergebene Attribut und protokolliere den alten und neuen Wert
        """
        val = newvals[key]
        setter_name = setters_map[key]
        setter_info = info_dict[setter_name]
        stem = '%(o)r: '  # sonst nicht gefunden?! §:-|
        if dryrun:
            stem = '<DRYRUN> '+ stem
        msg = stem + 'setting %(key)r to %(val)r%(setter_info)s'
        if oldvals is None:
            getter_name = getters_map[key]
            if getter_name is not None:
                ga = getattr(o, getter_name)
                old = ga()
                msg += ' (was %(old)r)'
        else:
            try:
                old = oldvals[key]
                msg += ' (was %(old)r)'
            except KeyError:
                pass
        if val not in (None, '') or 'old' not in locals():
            logger.info(msg, locals())
        else:
            logger.info(stem + 'deleting %(key)r%(setter_info)s, was %(old)r', locals())
        # dryrun heißt nur: keine Zuweisung; aber ob der Setter existiert,
        # wollen wir durchaus wissen!
        if setter_name is not None:
            a = getattr(o, setter_name)
        if dryrun:
            return
        if setter_name is None:
            setattr(o, key, val)
        else:
            a(val)

    return set_attribute

