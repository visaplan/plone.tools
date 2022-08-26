# -*- coding: utf-8 -*- vim: tw=79 cc=+1 sw=4 sts=4 et si
"""
visaplan.plone.tools: attools: Archetypes-related tools (_at3)
"""

def instance_and_label(instance, brain, verbose):
    if instance is None:
        instance = brain.getObject()
        if verbose:
            iinfo = brain.getURL()
    elif verbose:
        iinfo = repr(instance)
    else:
        iinfo = None
    return instance, iinfo


def getter_name(a):
    """
    >>> getter_name('userId')
    'getUserId'
    """
    return 'get%s%s' % (a[0].upper(), a[1:])


def getter_tuple(a):
    """
    Gib ein 2-Tupel aus Feldname und Getter-Name zurück
    """
    return (a, getter_name(a))


def setter_name(a):
    """
    >>> setter_name('userId')
    'setUserId'
    """
    return 'set%s%s' % (a[0].upper(), a[1:])


def setter_tuple(a):
    """
    Gib ein 2-Tupel aus Feldname und Setter-Name zurück
    """
    return (a, setter_name(a))
