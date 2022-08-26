# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _uid
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types
from six import text_type as six_text_type

# Zope:
from Products.CMFCore.utils import getToolByName

# Local imports:
from visaplan.plone.tools._have import HAS_KITCHEN

if HAS_KITCHEN:
    # visaplan:
    from visaplan.kitchen.spoons import generate_uids
else:
    generate_uids = None

# Logging / Debugging:
from pdb import set_trace
from visaplan.tools.debug import pp

__all__ = [
        'make_distinct_finder',
        'make_uid_setter',
        'make_uid_collector',
        ]


def make_distinct_finder(**kwargs):
    """
    Erzeuge eine Funktion, die ein per UID angegebenes Objekt findet;
    bei uneindeutigem Ergebnis, oder wenn nicht gefunden, tritt ein Fehler auf.
    """
    if 'catalog' not in kwargs:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    else:
        catalog = kwargs.pop('catalog')
    logger = kwargs.pop('logger')

    def find_one(**kwargs):
        """
        Finde exakt ein Objekt und gib das "brain" zurück.
        Derzeit wird nur nach UIDs gesucht ...
        """
        if 'uid' in kwargs:
            uid = kwargs.pop('uid')
        elif 'uid' in kwargs:
            uid = kwargs.pop('UID')
        else:
            raise ValueError('UID/uid needed; got %(kwargs)s', locals())
        query = {'UID': uid}
        brains = catalog(query)
        if not brains:
            raise ValueError('UID %(UID)r not found!', locals())
        elif brains[1:]:
            number = len(brains)
            raise ValueError('%(number)d hits for UID %(UID)r;'
                             ' *one* expected!',
                             locals())
        return brains[0]

    return find_one


def make_uid_setter(**kwargs):
    """
    Erzeuge eine Funktion, die die UID einer bekannten Ressource setzt;
    es wird nichts neu erzeugt
    """
    if 'catalog' not in kwargs:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    else:
        catalog = kwargs.pop('catalog')
    logger = kwargs.pop('logger')

    find_one = make_distinct_finder(catalog=catalog, logger=logger)

    # Vorgabewerte:
    optional = kwargs.pop('optional', False)
    shortcircuit = kwargs.pop('shortcircuit', False)
    if kwargs:
        logger.error('make_uid_setter: unused arguments! (%(kwargs)r)', locals())

    if 'portal' not in kwargs:
        if 'context' in kwargs:  # might have been popped above already
            context = kwargs.pop('context')
        site = getToolByName(context, 'portal_url')
    else:
        site = kwargs.pop('portal')

    def visible_path(s):
        """
        >>> visible_path('/gkz/meine-kurse')
        '/meine-kurse'
        """
        assert s.startswith('/')
        liz = s.split('/')
        del liz[1]
        return '/'.join(liz)

    def set_uid(uid_new, path, uid_old=None,
                optional=optional,
                shortcircuit=shortcircuit):
        """
        uid_new -- die neue UID (jedenfalls benötigt)
        path -- ein Pfad, oder eine Sequenz von Pfaden (benötigt)
        uid_old -- optional; darf, wenn angegeben, nicht gleich uid_new sein

        optional -- das übergebene Dings ist optional; wenn es fehlt, ist das
                    nicht schlimm (aber wenn es da ist, soll es die angegebene
                    UID bekommen)
        shortcircuit -- Wenn mehrere Pfade angegeben wurden, nach dem ersten
                        Treffer aufhören zu suchen; ansonsten wird auch
                        geprüft, ob die anderen ebenfalls da sind, und dies
                        ggf. protokolliert
        """
        if isinstance(path, six_string_types):
            paths = [path]
        elif path:
            paths = tuple(path)
        else:
            paths = []
        brain_new = find_one(uid=uid_new)
        if uid_old:
            if uid_old == uid_new:
                raise ValueError('Different UIDs expected, got: %(uid_new)r'
                                 % locals())
            brain_old = find_one(uid=uid_old)
            if brain_old and brain_new:
                logger.fatal('set_uid: Both old (%(uid_old)r) and new '
                             '(%(uid_new)r) UIDs founc!', locals())
                return False
            o_old = brain_old.getObject()
            logger.info('Setting UID of %(o_old)r to %(uid_new)r'
                        ' (was: %(uid_old)r', locals())
            o_old._setUID(uid_new)
            return True

        if brain_new:
            path_new = visible_path(brain.getPath)
            if paths:
                if path_new in paths:
                    logger.info('Found UID %(uid_new)r in expected path'
                                ' %(path_new)r', locals())
                else:
                    logger.warn('Found UID %(uid_new)r in UNEXPECTED path'
                                ' %(path_new)r (expected: %(paths)s)', locals())
            else:
                logger.info('Found UID %(uid_new)r in path'
                            ' %(path_new)r (no expectations specified)',
                            locals())
            return True

        # keine Treffer über UIDs; jetzt nach Pfaden suchen:
        done = False
        for pa in paths:
            logger.info('seeking %(pa)r ...', locals())
            o = site.restrictedTraverse(pa)
            if o:
                if done:
                    logger.warn('ignoring %(o)r', locals())
                else:
                    logger.info('setting UID of %(o)r to %(uid_new)r', locals())
                    o._setUID(uid_new)
                    done = True
                    if shortcircuit:
                        break

        if done:
            return True
        elif optional:
            logger.info('Nothing found (new uid: %(uid_new)r,'
                        ' paths: %(paths)r',
                        locals())
            return False
        else:
            logger.error('Nothing found! (new uid: %(uid_new)r,'
                         ' paths: %(paths)r',
                         locals())
            return False

    return set_uid


def make_uid_collector(getbyuid, transform, extract=generate_uids,
                       theset=None,
                       expect='brain',
                       **kwargs):
    """
    Erzeuge eine Funktion, die rekursiv UIDs extrahiert und in einem Set
    sammelt; Rückgabewert ist ein Tupel (Funktion, Set).

    getbyuid - eine Funktion, die für eine gegebene UID das jeweilige
               Katalogobjekt zurückgibt
    extract - eine Funktion, die aus dem (ggf. durch die transform-Funktion
              ergänzten) Text die UIDs erzeugt
    transform - eine Transformationsfunktion, die den "rohen" Text expandiert
                und Einbettungen von Ressourcen auswertet
    theset - das Set (ggf. neu erzeugt)
    expect - einziger implementierter Wert: 'brain'

    Nur als benannte Option:

    debug_uids - eine Menge/Sequenz von UIDs, bei denen set_trace aufgerufen
                 werden soll. In diesem Fall wird eine spezielle Version der
                 Funktion erzeugt, die spezielle Debugging-Informationen
                 vorhält.
    debug_label - zur Information, welcher UID-Collector die aktuelle
                  Unterbrechung ausgelöst hat

    ACHTUNG:
    - die Vorhaltung des kompletten Rohtexts im Indexobjekt entspricht nicht
      den "best practices" für Plone;
    - es wird hier hartcodiert bislang nur der Wert des Felds "text" untersucht;
    - bei Dexterity-Objekten würde sich hier die Notwendigkeit diverser
      Änderungen ergeben!
    """
    if theset is None:
        theset = set()

    if expect != 'brain':
        raise ValueError('expect=%(expect)r not implemented!' % locals())

    if extract is None:
        raise ValueError('No extract function given!')

    def collect_uids(brain):
        """
        Rekursives Unterprogramm zur Extraktion von UIDs

        Argumente:
        - brain - ein Katalogeintrag
        """
        if not brain:
            return
        myuid = brain.UID
        if myuid in theset:
            return
        theset.add(myuid)
        text = brain.getRawText
        if not text:
            return
        elif transform is None:
            pass
        else:
            if isinstance(text, six_text_type):
                space = u' '
            else:
                space = ' '
            text += space + transform(text)
        for uid in extract(text=text):
            if uid in theset:
                continue
            collect_uids(getbyuid(uid))

    debug_uids = kwargs.pop('debug_uids', None)
    if not debug_uids:
        return collect_uids, theset
    debug_label = kwargs.pop('debug_label', None) or None
    if debug_label is None:
        headline = 'WATCHED CASE: uid %(uid)r found!'
    else:
        headline = ('WATCHED CASE (%(debug_label)s): uid %%(uid)r found!'
                    ) % locals()

    def collect_uids_2(brain, depth=0, stack=None):
        """
        Rekursives Unterprogramm zur Extraktion von UIDs

        Argumente:
        - brain - ein Katalogeintrag
        """
        if not brain:
            return
        myuid = brain.UID
        if myuid in theset:
            return
        theset.add(myuid)
        text = brain.getRawText
        if not text:
            return
        elif transform is None:
            pass
        else:
            if isinstance(text, six_text_type):
                space = u' '
            else:
                space = ' '
            text += space + transform(text)
        if stack is None:
            stack = [myuid]
        for uid in extract(text=text):
            if uid in theset:
                continue
            if uid in debug_uids:
                ppargs = [
                    headline % locals(),
                    ('myuid:', myuid),
                    ('depth:', depth),
                    ('stack:', stack),
                    ]
                if isinstance(debug_uids, dict):
                    uidinfo = debug_uids[uid]
                    ppargs.insert(1, ('UID-Info:', uidinfo))
                if 0 and 'debug collect_uids_2':
                    pp(ppargs)
                    set_trace()
            collect_uids_2(getbyuid(uid), depth+1, stack+[uid])

    return collect_uids_2, theset

