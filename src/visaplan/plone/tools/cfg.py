# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
visaplan.plone.tools.cfg: Zugriff auf "Produkt"konfiguration ...

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

Siehe auch:

- visaplan.tools.dicts.getOption

sowie die als Factory (zur Konversion der Strings zu den benötigten Datentypen)
vorgesehenen Funktionen

- visaplan.tools.minifuncs.makeBool
- visaplan.tools.minifuncs.NoneOrInt
- ...
- visaplan.tools.lands0.makeListOfStrings
"""

__all__ = ['get_debug_active',
           'get_raw_config',
           'get_config',
           'split_filename',
           ]

# Standardmodule:
from os.path import normpath, sep, splitext
from collections import defaultdict
from traceback import extract_stack
from logging import getLogger

logger = getLogger('visaplan.plone.tools')

# for convenience/development:
try:
    # Plone/Zope:
    from App.config import getConfiguration
    # Unitracc-Tools:
    from visaplan.tools.minifuncs import makeBool, NoneOrString
except ImportError:
    if __name__ != '__main__':
        raise

# Unitracc-Tools:
from visaplan.tools.minifuncs import makeBool, NoneOrString

def get_debug_active(product, default=None):
    """
    Lies den Konfigurationswert 'debug_active' für das übergebene Produkt aus.
    Das Ergebnis ist ein Wahrheitswert oder eine Ganzzahl.
    """
    try:
        dic = getConfiguration().product_config.get(product, {})
    except AttributeError as e:
        logger.warn('get_debug_active(%(product)r):'
                    ' Can\'t read configuration!',
                    locals())
        logger.exception(e)
    except KeyError as e:
        logger.warn('get_debug_active(%(product)r):'
                    ' obviously no configuration for this product!',
                    locals())
        logger.exception(e)
    else:
        if 'debug-active' in dic:
            raise ValueError('Fehlerhafte Konfiguration fuer Produkt'
                             ' %(product)r!'
                             % locals())
        val = dic.get('debug_active', '')
        return makeBool(val, default)
    # in case of errors: 
    logger.info('get_debug_active(%(product)r):'
                ' using default %(default)r',
                locals())
    return makeBool(default)


def get_raw_config(product=None, defaults={}, fn=None):
    """
    Lies die Konfiguration für das übergebene Produkt aus
    und gib das "rohe" Dictionary zurück (ohne jegliche Wertekonversion).

    Schlüssel, die in der Konfiguration fehlen,
    werden ggf. dem defaults-dict entnommen.

    Siehe auch visaplan.tools.dicts.getOption
    """
    if fn is not None:
        if product is not None:
            raise ValueError('Bitte nur entweder <product> (%(product)r)'
                             ' oder <fn> (%(fn)r) angeben!'
                             % locals())
        product = split_filename(fn)[0]

    dic = getConfiguration().product_config.get(product, {})
    if defaults:
        defaults.update(dic)
        return defaults
    else:
        return dic


# TODO: optionale Umgebungsvariablen ("veraltend") unterstützen,
#       z. B. W3L_URL (<product>_<key>);
#       siehe pdf/config.py
def get_config(**kwargs):
    """
    Lies die Konfiguration für das übergebene Produkt aus
    und gib ein Dict. mit konvertierten Werten zurück

    Alle Argumente sind semantisch optional und müssen daher sinnvollerweise
    benannt angegeben werden; allerdings wird genau eine Option aus <product>
    und <fn> benötigt (wie für --> get_raw_config), und die Angabe von
    <factories> wird praktisch immer benötigt.

    Optionen:
    fn -- Dateiname, üblicherweise des aufrufenden Moduls (__file__)
    product -- alternativ: Name des konfigurierten Produkts
    defaults -- Vorgabewerte (Dict)
    factories -- Dict. von Funktionen, die aus den Konfigurations- oder, wenn
                 fehlend, Vorgabewerten die zu verwendenen Werte erzeugen

    Alle Schlüssel sollten mindestens in einem der Argumente <factories> oder
    <defaults> explizit sein; im jeweils anderen können sie über den
    defaultdict-Mechanismus kommen.
    """
    if 'fn' in kwargs:
        assert 'product' not in kwargs, (
                'Bitte nur *entweder* fn (%(fn)r)'
                ' *oder* product (%(product)r) angeben!'
                ) % locals()
        fn = kwargs.pop('fn')
        product = split_filename(fn)[0]
    else:
        product = kwargs.pop('product')
    factories = kwargs.pop('factories', None)
    if factories is None:
        factories = defaultdict(NoneOrString)
    dic = kwargs.pop('defaults', {})
    conf = getConfiguration().product_config.get(product, {})
    dic.update(conf)

    fact_keys = set(factories.keys())
    done_keys = set()
    for key, val in dic.items():
        done_keys.add(key)
        if isinstance(val, basestring):
            dic[key] = factories[key](val)
    fact_keys.difference_update(done_keys)
    for key in fact_keys:
        # klappt, wenn defaults ein defaultdict ist:
        dic[key] = factories[key](dic[key])
    return dict(dic)


def split_filename(fn, name=None,
                   prefix=None, suffix=None,
                   stack_limit=2):
    """
    Ermittle einen Namen und ein Label aus dem Dateinamen,
    der ggf. aus dem Aufrufstack ermittelt wird.

    Zunächst "richtige" Entwicklungs- oder installierte Quellen:

    >>> split_filename('/opt/zope/instances/unitracc-devel/src/visaplan.plone.tools/src/visaplan/plone/tools/log.py')
    ('visaplan.plone.tools', 'visaplan.plone.tools:log (DEV)')
    >>> split_filename('/opt/zope/common/eggs/visaplan.tools-1.0-py2.7.egg/visaplan/tools/__init__.py')
    ('visaplan.tools', 'visaplan.tools')
    >>> split_filename('/opt/zope/common/eggs/visaplan.tools-1.1-py2.7.egg/src/visaplan/tools/misc.py')
    ('visaplan.tools', 'visaplan.tools:misc')

    Nun die historischen Varianten:

    >>> split_filename('/.../Products/unitracc/browser/tan/browser.py')
    ('tan', 'unitracc@@tan')
    >>> split_filename('/.../Products/zkb/browser/projectreview/browser.py')
    ('projectreview', 'zkb@@projectreview')
    >>> split_filename('/.../Products/unitracc/adapters/sqlwrapper/adapter.py')
    ('sqlwrapper', 'unitracc->sqlwrapper')

    Hilfsmodule:
    >>> split_filename('/.../Products/unitracc/browser/tan/utils.py')
    ('tan', 'unitracc@@tan:utils')

    Sonstiges (Name für Settings noch nicht fix):
    >>> split_filename('/.../Products/unitracc/upgrades/to_20236.py')
    ('to_20236_oder_so', 'unitracc:upgrades:to_20236')
    >>> split_filename('/.../Products/unitracc/tools/misc.py')
    ('misc_oder_so', 'unitracc:tools:misc')

    Die Unterstützung des Aufrufs aus Fremdpaketen ist noch etwas umständlich:
    >>> split_filename('/.../src/visaplan.UnitraccShop/src/visaplan/UnitraccShop/__init__.py',
    ...                name='visaplan.UnitraccShop',
    ...                prefix='')
    ('visaplan.UnitraccShop', 'visaplan.UnitraccShop')

    Der folgende Aufruf zeitigt noch nicht das gewünschte Ergebnis:
    >-> split_filename('.../src/Products.unitracc/src/Products/unitracc/browser/viewpreview/browser.pyc')
    ('Products.unitracc', 'Products.unitracc@@viewpreview (DEV)')
    """
    if name:
        if prefix is None:
            prefix = 'unitracc@@'
        if suffix is None:
            suffix = ''
        return (name,
                '%(prefix)s%(name)s%(suffix)s' % locals())

    if fn is None:
        raw_info = extract_stack(limit=stack_limit)
        fn = raw_info[0][0]

    lst = normpath(fn).split(sep)  # alle
    _pkg, _mod, _devel = split_srcfilename(lst)
    if _pkg is not None:
        _label = _pkg
        if _mod is not None:
            _label += ':'+_mod
        if _devel:
            _label += ' (DEV)'
        return (_pkg, _label)
    _prefix = None
    _name = None
    _suffix = None
    _fn = lst.pop()
    lst2 = list(lst)
    _fn_base, _fn_ext = splitext(_fn)
    _dn = lst.pop()
    _pn = lst.pop()  # parent name ('browser')
    _Pn = lst.pop()  # Product name ('unitracc')
    if _fn_base == 'adapter':
        _prefix = _Pn + '->'
        _name = _dn
        _suffix = ''
    elif _fn_base == 'browser':
        _prefix = _Pn + '@@'
        _name = _dn
        _suffix = ''
    elif _pn.startswith('browser'):
        _prefix = _Pn + '@@'
        _name = _dn
        _suffix = ':'+_fn_base
    elif _pn.startswith('adapter'):
        _prefix = _Pn + '->'
        _name = _dn
        _suffix = ':'+_fn_base
    else:
        try:
            pi = lst2.index('Products')
            return (_fn_base+'_oder_so',
                    ':'.join(lst2[pi+1:] + [_fn_base]),
                    )
        except ValueError as e:
            print(str(e))
            return '?'.join(lst2)
            raise ValueError('Unsupported filename: %(fn)r' % locals())
    if prefix is None:
        prefix = _prefix
    if name is None:
        name = _name
    if suffix is None:
        suffix = _suffix
    return (name,
            '%(prefix)s%(name)s%(suffix)s' % locals())


def parse_egg_dirname(dn):
    """
    Extrahiere die folgenden Informationen aus dem Namen:

    - den Paketnamen
    - die Versionsangabe
    - das Python-Versionstupel

    >>> parse_egg_dirname('visaplan.tools-1.0-py2.7.egg')
    ('visaplan.tools', '1.0', (2, 7))

    Sonstige Namen werden nicht erkannt:
    >>> parse_egg_dirname('visaplan.tools')
    (None, None, None)
    """
    if not dn.endswith('.egg'):
        return (None, None, None)
    lapypo = dn.rfind('-py')
    if lapypo == -1:
        return (None, None, None)
    endofpa = dn[:lapypo].rfind('-')
    if endofpa == -1:
        return (None, None, None)
    pa = dn[:endofpa]
    pv = dn[endofpa+1:lapypo]
    pyraw = dn[lapypo+3:-4]
    try:
        pytup = tuple(map(int, pyraw.split('.')))
    except ValueError:
        return (None, None, None)
    else:
        return pa, pv, pytup


def _pkg_and_submodule(pkg, tail):
    """
    >>> _pkg_and_submodule('visaplan.tools', ['visaplan', 'tools', 'coding.py'])
    ('visaplan.tools', 'coding')
    >>> _pkg_and_submodule(['visaplan', 'tools'], ['visaplan', 'tools', '__init__.py'])
    ('visaplan.tools', None)
    """
    if isinstance(pkg, basestring):
        pkg_as_list = pkg.split('.')
    else:
        pkg_as_list, pkg = pkg, '.'.join(pkg)
    pkg_len = len(pkg_as_list)
    if tail[:pkg_len] != pkg_as_list:
        raise ValueError('tail %(tail)r mismatches package %(pkg)r!'
                         % locals())
    if not tail[pkg_len:]:
        return pkg, None
    modfile = tail.pop()
    module, ext = splitext(modfile)
    if module == '__init__':
        return pkg, '.'.join(tail[pkg_len:]) or None
    return pkg, '.'.join(tail[pkg_len:]+[module])


def split_srcfilename(fn):
    """
    Nimm den Namen einer Python-Datei entgegen und extrahiere hieraus drei
    Informationen:
    - das Paket
    - das Modul
    - handelt es sich um eine Entwicklungsressource?

    >>> split_srcfilename('/opt/zope/common/eggs/visaplan.tools-1.0-py2.7.egg/visaplan/tools/coding.py')
    ('visaplan.tools', 'coding', False)
    >>> split_srcfilename('/opt/zope/common/eggs/visaplan.tools-1.1-py2.7.egg/src/visaplan/tools/misc.py')
    ('visaplan.tools', 'misc', False)
    >>> split_srcfilename('/opt/zope/common/eggs/visaplan.tools-1.0-py2.7.egg/visaplan/tools/__init__.py')
    ('visaplan.tools', None, False)
    >>> split_srcfilename('/opt/zope/instances/unitracc-devel/src/visaplan.plone.tools/src/visaplan/plone/tools/log.py')
    ('visaplan.plone.tools', 'log', True)
    >>> split_srcfilename('.../src/visaplan.tools/src/visaplan/tools/debug.py')
    ('visaplan.tools', 'debug', True)
    >>> split_srcfilename('.../src/visaplan.tools/visaplan/tools/coding.py')
    ('visaplan.tools', 'coding', True)

    Fallback-Wert für Pfade ohne src- eder egg-Komponente (kein Paket erkannt):

    >>> split_srcfilename('/some/strange/unexpected/path.py')
    (None, '.../strange/unexpected/path.py', True)

    Der folgende Aufruf zeitigt noch nicht das gewünschte Ergebnis:
    >-> split_srcfilename('.../src/Products.unitracc/src/Products/unitracc/browser/viewpreview/utils.pyc')
    """
    if isinstance(fn, basestring):
        fn_list = fn.split(sep)
    else:
        fn_list = list(fn)
    i = 0
    src_positions = []
    package_name = None
    for chunk in fn_list:
        if chunk == 'src':
            src_positions.append(i)
        else:
            _pn = parse_egg_dirname(chunk)[0]
            if _pn is not None:
                package_name = _pn
                i += 1
                break
        i += 1

    if package_name is not None:
        if fn_list[i] == 'src':
            i += 1
        return _pkg_and_submodule(package_name, fn_list[i:]) + (False,)

    # kein Egg; 
    src_bases = src_positions[-2:]
    if src_bases[1:]:  # ja, es gibt (mindestens) zwei:
        sb1, sb2 = src_bases
        if sb2 <= sb1 + 1:
            raise ValueError('.../src/src/... ?! (%(sb1)d, %(sb2)d)'
                             % locals())
        return _pkg_and_submodule(fn_list[sb1+1], fn_list[sb2+1:]) + (True,)
    elif src_bases:
        sb1 = src_bases[0]
        return _pkg_and_submodule(fn_list[sb1+1], fn_list[sb1+2:]) + (True,)
    return (None,
            sep.join(['...']
                     +fn_list[-3:]
                     ),
            True)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
