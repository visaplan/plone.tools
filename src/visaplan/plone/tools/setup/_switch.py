# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Switch objects on/off for search and navigation use
"""

__all__ = [
        'switch_menu_item',
        'show_item',
        'hide_item',
        ]


def switch_menu_item(o, on, logger, strict=True):
    """
    (De-) Aktiviert ein Objekt (i.d.R. einen Ordner) für das Menü

    o -- das Objekt
    on - der Wahrheitswert; die Negation wird verwendet als neuer Wert für excludeFromNav
         NEU in Version 1.4+: keine Änderung, wenn None!
    logger - der Logger
    strict - wenn True (Vorgabe), werden für `on` nur Wahrheitswerte akzeptiert
    """
    if on is None:
        logger.info('%(o)r.switch_menu_item: not changed (%(on)r)', locals())
        return
    elif strict and on not in (True, 1, False, 0):
        raise ValueError('Boolean value expected (%(on)r; for %(o)r)'
                         % locals())
    val = not on
    o.setExcludeFromNav(val)
    o.reindexObject()
    logger.info('%(o)r: setExcludeFromNav(%(val)r)', locals())


def show_item(o, logger, on=True):
    """
    Stellt ein Objekt für die Suche zur Verfügung.

    o -- das Objekt
    on - der Wahrheitswert; die Negation wird verwendet als neuer Wert für excludeFromSearch
    logger - der Logger
    """
    val = not on
    o.setExcludeFromSearch(val)
    o.reindexObject()
    logger.info('%(o)r: setExcludeFromSearch(%(val)r)', locals())


def hide_item(o, logger):
    """
    Verbirgt ein Objekt vor der Suche.

    o -- das Objekt
    logger - der Logger
    """
    show_item(o, logger, False)
