# -*- coding: utf-8 -*-
"""
ZCML-Generierung für Plone-Ressourcen

Verwendung:
    from visaplan.plone.tools.zcmlgen import TemplateGenerator
    TemplateGenerator(__file__).write()

TO DO:
- Bislang haben wir spezialisierte Generatoren, die nur jeweils eine Sorte von
  Einträgen erzeugen.
  Wünschenswert wäre:
  - eine Generierung aller unterstützten Typen durch einen allgemeinen
    Generator
  - eine Gruppierung nach Typen
"""

# Standardmodule
from os.path import join, isdir, isfile, split, abspath, normcase, sep
from os import listdir
from difflib import Differ

import sys
from pdb import set_trace

# Zope/Plone
try:
    from Globals import DevelopmentMode
except ImportError:
    if __name__ == '__main__':
    	DevelopmentMode = True
    else:
    	raise

from visaplan.plone.base.exceptions import OutdatedFileError, MissingFileError

__all__ = [
        'BasicGenerator',
        'TemplateGenerator',
        'ResourceGenerator',
        'SubpackageGenerator',
        # Hilfsfunktionen:
        'make_plonename_factory',
        'changeable_path',
        ]


# -------------------------------------------- [ Daten ... [
_FRAME = """<configure
    xmlns="http://namespaces.zope.org/zope"
    xmlns:browser="http://namespaces.zope.org/browser">
    %s
</configure>
"""

RESOURCE = """
    <browser:resource
             name="%(filename)s"
             file="%(filename)s"
             />
"""

SUBPACKAGE = """
    <include package=".%(name)s" />
"""

PAGE = """
    <browser:page
             for="*"
             name="%(name)s"
             template="%(filename)s"
             permission="zope2.View"
             />
"""

_DENIED = frozenset(['__init__.py',
                     'configure.zcml',
                     '.svn'])
# -------------------------------------------- ] ... Daten ]


class BasicGenerator(object):
    """
    Abstrakte Basisklasse;
    fehlende Methoden z. B. in ResourceGenerator definiert
    """
    def __init__(self, fn):
        dirname, filename = split(fn)
        self.base_path = abspath(dirname)
        self.blacklist = set(_DENIED)
        # die generierende Datei bleibt außen vor:
        self.blacklist.add(filename)
        self.zcml_name = join(self.base_path, 'configure.zcml')

    def __repr__(self):
        return '<%s(%s/)>' % (self.__class__.__name__, self.base_path)

    def skip(self, fn, skipdirs=True):
        """
        Soll die aktuelle Datei übergangen werden?

        fn -- der Datei- (oder Verzeichnis-) -name
        skipdirs -- wenn True, werden Verzeichnisse generell ignoriert;
                    wenn False, werden Nicht-Verzeichnisse ignoriert
                    (SubpackageGenerator)
        """
        if fn in self.blacklist:
            return True
        elif fn.startswith('.'):
            return True
        elif fn.endswith('.pyc'):
            return True
        elif fn.endswith('.pyo'):
            return True
        elif fn.endswith('~'):
            return True
        elif fn.endswith('.orig'):
            return True
        elif isdir(join(self.base_path, fn)):
            return skipdirs
        else:
            return not skipdirs

    def generate_list(self):
        tmpls = []
        ENTRY_MASK = self._entry_mask()
        for dict_ in self.generate_dicts():
            tmpls.append(ENTRY_MASK % dict_)
        return tmpls

    def generate_text(self):
        return _FRAME % ''.join(self.generate_list())

    def write(self, devmode=None):
        txt = self.generate_text()
        fn = self.zcml_name
        found = isfile(fn)
        if found:
            with open(fn, 'ru') as fp:
                old = fp.read()
                if self.diff(old, txt):
                    return
        if devmode is None:
            devmode = DevelopmentMode
        if not changeable_path(fn, devmode):
            if found:
                raise OutdatedFileError(filename=fn)
            else:
                raise MissingFileError(filename=fn)
        with open(fn, 'w') as fp:
            fp.write(txt)

    def diff(self, old, new):
        """
        Gib (in Anlehnung an das Kommandozeilen-Tool) True zurück,
        wenn nichts geändert; ansonsten False.

        Ignoriere Leerzeilen.
        """
        def skipempty(s):
            return not s.rstrip()
        differ = Differ(linejunk=skipempty)
        oldl = [line.strip()
                for line in old.splitlines()
                ]
        newl = [line.strip()
                for line in new.splitlines()
                ]
        # a Generator object is "True", even if yielding an empty list ...
        difflines = list(differ.compare(oldl, newl))
        # Differ creates a human-readable difference; lines prefixed by '  '
        # are common to both
        if [difference
            for difference in difflines
            if not difference.startswith('  ')  # unchanged lines
            and difference not in ('+ ', '- ')  # empty lines added/removed
            ]:
            print('\n'.join(difflines))
            if sys.stdout.isatty():
                set_trace()
            return False
        return True


class ResourceGenerator(BasicGenerator):
    """
    implementiert die fehlenden Methoden der BasicGenerator-Klasse
    für statische Ressourcen
    """

    def generate_dicts(self):
        for fn in sorted(listdir(self.base_path)):
            if self.skip(fn):
                continue
            dic = {'filename': fn,
                   'name': fn,
                   }
            yield dic

    def _entry_mask(self):
        return RESOURCE


class SubpackageGenerator(BasicGenerator):
    """
    implementiert die fehlenden Methoden der BasicGenerator-Klasse
    für Unterpakete
    """

    def generate_dicts(self):
        for fn in sorted(listdir(self.base_path)):
            if self.skip(fn, skipdirs=False):
                continue
            fullname = join(self.base_path, fn)
            considered_package = False
            # when we find one, we expect the other to be present as well!
            # If either is missing, there will be (most likely) some error,
            # but this is not to be solved *here*.
            for pfn in ('__init__.py',
                        'configure.zcml',
                        ):
                if isfile(join(fullname, pfn)):
                    considered_package = True
                    break
            if considered_package:
                yield {'name': fn,
                       }

    def _entry_mask(self):
        return SUBPACKAGE


def make_plonename_factory(ext):
    """
    Erzeugt eine Funktion, die für einen gegebenen Dateinamen
    den aufrufbaren Namen im Plone-Kontext zurückgibt.

    >>> f = make_plonename_factory('.pt')
    >>> f.__name__
    'make_plonename.pt'
    >>> f('test.py')
    >>> f('test.pt')
    'test'
    """
    if not ext.startswith('.'):
        raise ValueError('.ext erwartet (%(ext)r erhalten)'
                         % locals())
    lext = len(ext)

    def make_plonename(fn):
        if fn.endswith(ext):
            return fn[:-lext] or None

    make_plonename.__name__ += ext
    return make_plonename


class TemplateGenerator(BasicGenerator):
    """
    Generator für Templates
    """

    def __init__(self, fn, aliases=(), aliasdict_func=None,
                 include_extensions=('.xml.pt', '.pt',
                                     )):
        """
        aliases-Funktionalität derzeit noch nicht in Verwendung
        """
        BasicGenerator.__init__(self, fn)

        if aliases:
            if isinstance(aliases, set):
                aliases = sorted(aliases)
            self.aliases = aliases
        else:
            self.aliases = None
        self.aliasdict_func = aliasdict_func
        self.whitelist_functions = [make_plonename_factory(ext)
                                    for ext in include_extensions
                                    ]

    def _entry_mask(self):
        return PAGE

    def generate_dicts(self):
        whitelist_functions = self.whitelist_functions
        for fn in sorted(listdir(self.base_path)):
            if self.skip(fn):
                continue
            pn = None  # Plone-Name
            for f in whitelist_functions:
                pn = f(fn)
                if pn is not None:
                    break
            if pn is None:
                print 'SKIPPING: %s' % join(self.base_path, fn)
                continue
            yield {'filename': fn,
                   'name': pn,
                   }

    def generate_list(self):
        tmpls = BasicGenerator.generate_list(self)
        if self.aliases:
            ENTRY_MASK = self._entry_mask()
            first_nondict = True
            func = None
            for alias in aliases:
                if not isinstance(alias, dict):
                    if first_nondict:
                        assert self.aliasdict_func is not None
                        assert callable(self.aliasdict_func)
                        func = self.aliasdict_func
                        first_nondict = False
                    alias = func(alias)
                tmpls.append(ENTRY_MASK % alias)
        return tmpls


def changeable_path(fullpath, devmode=None):
    """
    Ist der übergebene Pfad einer, in dem wir eine Datei zu ändern versuchen?

    Im empfohlenen Plone-Setup hat der laufende Zope-Prozeß keine Schreibrechte
    in den Programmquellen.  Zur Entwicklung ist es dennoch praktisch,
    bestimmte Dateien automatisch generieren zu können, z. B.
    Versionsinformationen oder einfache configure.zcml-Dateien.

    Die vorgeschlagene Logik ist wie folgt:

    1. Prüfen, ob die Zieldatei schon den erwarteten Wert enthält
       (nicht Bestandteil dieser Funktion).
       Wenn ja, dann sind weitere Aktionen unnötig.
    2. Prüfen, ob die fragliche Datei nach ihrem Namen und ggf. dem übergebenen
       globalen Entwicklungsmodus änderbar ist
       (diese Funktion).
       Wenn nein: eine Ausnahme werfen, um den Start der Instanz zu verhindern,
       damit dieses Faktum nicht unbemerkt bleibt!
    3. Die Änderung versuchen.
       Dabei kann natürlich dennoch ein OSError auftreten; das wäre dann evtl.
       ein Anlaß, die Vorab-Prüfung zu verfeinern.

    Dateien mit den Namen 'version.txt' oder 'configure.zcml' dürfen in
    Entwicklungspaketen geändert werden:
    >>> changeable_path('.../src/visaplan.cool.tool/src/.../version.txt')
    True
    >>> changeable_path('.../src/visaplan.cool.tool/src/.../configure.zcml')
    True

    Andere Dateinamen werden zurückgewiesen:
    >>> changeable_path('.../src/visaplan.cool.tool/src/.../otherfile.txt')
    False

    In Eggs wird generell nichts geändert:
    >>> changeable_path('.../eggs/visaplan.cool.tool-1.0-py2.7.egg/src/.../configure.zcml')
    False
    """
    splitpath = normcase(abspath(fullpath).split(sep))
    filename = splitpath.pop()
    # TODO: normcase for whitelist
    if filename not in ('version.txt',
    	                'configure.zcml',
    	                ):
    	return False
    for seg in splitpath:
    	if seg.endswith('.egg'):
    	    return False
    if not set(['src', 'Products']).intersection(splitpath):
    	return False
    if devmode is None:
    	devmode = DevelopmentMode
    return devmode or False


if __name__ == '__main__':
    import doctest
    doctest.testmod()
