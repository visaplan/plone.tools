# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
(Mock-Version, nur für Testzwecke)

unitracc.tools.cfg: Zugriff auf "Produkt"konfiguration ...

... in buildout-Skript:

    zope-conf-additional +=
        <product-config name>
            debug_active 1
        </product-config>

(kopiert nach ../../../parts/instance/etc/zope.conf, führender Leerraum wird
entfernt)

ACHTUNG - Der Defaultwert für get_debug_active muß ein String sein; z. B.:

    from Globals import DevelopmentMode
    from Products.unitracc.tools.cfg import get_debug_active
    debug_active = get_debug_active('tree', str(DevelopmentMode))

"""

__all__ = ['get_debug_active',
           'get_raw_config',
           ]

from visaplan.tools.minifuncs import makeBool


class MockConfiguration(object):
    product_config = {}


def getConfiguration(*args, **kwargs):
    """
    Dummy: gib ein leeres dict zurück
    """
    return MockConfiguration()

def get_debug_active(product, default=None):
    """
    Lies den Konfigurationswert 'debug_active' für das übergebene Produkt aus.
    Das Ergebnis ist ein Wahrheitswert oder eine Ganzzahl.
    """
    dic = getConfiguration().product_config.get(product, {})
    val = dic.get('debug_active', '')
    return makeBool(val, default)


def get_raw_config(product, defaults={}):
    """
    Lies die Konfiguration für das übergebene Produkt aus
    und gib das "rohe" Dictionary zurück (ohne jegliche Wertekonversion).

    Schlüssel, die in der Konfiguration fehlen,
    werden ggf. dem defaults-dict entnommen.
    """
    dic = getConfiguration().product_config.get(product, {})
    if defaults:
        defaults.update(dic)
        return defaults
    else:
        return dic
