# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps")
"""

# Standardmodule
from string import capitalize
from collections import defaultdict
from functools import wraps
from time import time

# Exceptions:
from ZODB.POSException import POSKeyError

# Plone, sonstiges:
from Products.CMFCore.utils import getToolByName
import transaction
from Products.CMFCore.WorkflowCore import WorkflowException

# Unitracc-Tools:
from visaplan.tools.classes import Proxy, GetterDict, CheckedSetterDict, DictOfSets
from visaplan.kitchen.spoons import generate_uids
from visaplan.tools.debug import pp
from visaplan.tools.minifuncs import gimme_False
from visaplan.tools.sequences import unique_union

# Logging und Debugging:
import logging
from pdb import set_trace

__all__ = ['switch_menu_item',  # Menüeintrag (de)aktivieren
           'show_item',
           'hide_item',
           'make_reindexer',
           'make_subfolder_creator',
           'make_attribute_setter',
           # 'make_mover',  (noch nicht implementiert)
           'make_renamer',
           'make_distinct_finder',
           'make_uid_setter',
           'make_uid_collector',
           # Workflow:
           'make_transition_applicator',
           # ... 'restricted' kann erfordern:
           'set_local_roles',
           # ... Hilfsfunktion hierfür erzeugen: 
           'make_simple_localroles_function',
           # sonstige Hilsfunktionen:
           'make_watcher_function',  # --> Signatur f(brain, string)
           # für Suche:
           'getAllLanguages',
           # Dekorator:
           'step',
           # noch unfertig: 
           # 'upgrade_step',
           # zugehörige Exception: 
           'StepAborted',
           # Helferlein für **kwargs: 
           'extract_object_and_brain', # --> (o, brain)
           'extract_object_or_brain',  # --> (o, brain=None)
           'extract_brain_or_object',  # --> (brain, o=None)
           ]


class StepAborted(Exception):
    """
    Vom Dekorator @step geworfen, wenn in einem Migrationsschritt eine
    KeyBoard-Exception ausgelöst wurde
    """

def switch_menu_item(o, on, logger):
    """
    (De-) Aktiviert ein Objekt (i.d.R. einen Ordner) für das Menü

    o -- das Objekt
    on - der Wahrheitswert; die Negation wird verwendet als neuer Wert für excludeFromNav
    logger - der Logger
    """
    val = not on
    o.setExcludeFromNav(val)
    o.reindexObject()
    logger.info('%(o)r: setExcludeFromNav(%(val)r)', locals())


def hide_item(o, logger):
    """
    Verbirgt ein Objekt vor der Suche.

    o -- das Objekt
    on - der Wahrheitswert; die Negation wird verwendet als neuer Wert für excludeFromSearch
    logger - der Logger
    """
    show_item(o, logger, False)


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


def make_subfolder_creator(**kwargs):
    """
    Erzeuge eine Funktion, die einen Ordner erzeugt und zurückgibt.
    Optionen, alle benannt zu übergeben:

    logger - der zu verwendende Logger
    title_factory - Funktion, um einen ggf. fehlenden Title zu erzeugen
    reindexer - wie von --> make_reindexer erzeugt

    Vorgabewerte für die zu erzeugende Funktion:

    switch_menu - True übergeben, um den neuen (oder schon existierenden)
                  Ordner explizit der Navigation hinzuzufügen
    parent - das schon existierende ordnerartige Elternobjekt
    view_id - die ID der aufzuschaltenden Ansicht
    """
    parent = kwargs.pop('parent', None)
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('new folder')
    title_factory = kwargs.pop('title_factory', None)
    if title_factory is None:
        title_factory = capitalize
    view_id = kwargs.pop('view_id', None)
    switch_menu = kwargs.pop('switch_menu', None)
    reindexer = kwargs.pop('reindexer', None)
    if switch_menu is not None:
        reindex = kwargs.pop('reindex', True)
    else:
        reindex = kwargs.pop('reindex', reindexer is not None
                                        or None)

    def new_folder(id, title=None, parent=parent,
                   view_id=view_id,
                   switch_menu=switch_menu,
                   reindex=reindex,
                   reindexer=reindexer,
                   **kwargs):
        new_child = getattr(parent, id, None)
        if new_child is None:
            if title is None:
                title = title_factory(id)
                logger.info('Default title for %(id)s is %(title)r', locals())
            logger.info('Creating folder %(parent)r/%(id)s (%(title)s)...',
                        locals())
            parent.manage_addFolder(id=id, title=title)
            new_child = getattr(parent, id)
        elif title is not None:
            logger.info('Ignoring new title %(title)r for existing %(new_child)r',
                        locals())
        if view_id:
            layout = new_child.getLayout()
            if layout == view_id:
                logger.info('%(new_child)r has layout %(view_id)r already', locals())
            else:
                logger.info('%(new_child)r/selectViewTemplate --> %(view_id)r', locals())
                new_child.selectViewTemplate(templateId=view_id)
        if switch_menu is not None:
            val = not switch_menu
            new_child.setExcludeFromNav(val)
            logger.info('%(new_child)r: setExcludeFromNav(%(val)r)', locals())
            if reindex and reindexer is None:
                reindexer = make_reindexer(logger=logger,
                                           context=parent)
        elif reindex is None:
            reindex = reindexer is not None
        if reindex:
            # import pdb; pdb.set_trace()
            reindexer(o=new_child)
        if kwargs:
            logger.warn('unused Arguments: %(kwargs)s', locals())
        return new_child

    return new_folder


"""
def safe_context_id(context_id):  (siehe --> ./misc.py, make_default_prefixer)
    ...
"""

def make_reindexer(**kwargs):
    """
    Erzeuge eine Funktion, die das übergebene Objekt reindiziert
    Optionen, alle benannt zu übergeben:

    logger - der zu verwendende Logger
    catalog - der Portalkatalog
    context - der Kontext; benötigt, wenn <catalog> nicht übergeben

    idxs - Liste der zu aktualisierenden Indexe
    update_metadata - sollen die Metadaten aktualisiert werden?
                      (Vorgabe: True)

    Vorgabewerte für die zu erzeugenden Funktion:

    update_metadata
    """
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('reindex')
    update_metadata = kwargs.pop('update_metadata', True)
    if update_metadata:
        idxs = kwargs.pop('idxs', None) or ['getId']
    else:
        idxs = kwargs.pop('idxs', ['getId'])
        if update_metadata is None and not idxs:
            update_metadata = True
            idxs = ['getId']
    ri_kwargs = {'update_metadata': update_metadata,
                 }
    if idxs:
        ri_kwargs['idxs'] = idxs
    catalog = kwargs.pop('catalog', None)
    if catalog is None:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    catalog_reindex = catalog.reindexObject
    return_brain = kwargs.pop('return_brain', False)
    if return_brain:
        get_brain = catalog._catalog
    _info = [update_metadata and 'update metadata' or 'no metadata',
             idxs and 'indexes: ' + ', '.join(idxs) or 'all indexes',
             return_brain and 'returning brains' or 'returning boolean'
             ]
    debug = kwargs.pop('debug', False)
    if debug:
        _info.append('DEBUG')

    logger.info('make_indexer: %s',
                '; '.join(_info))

    def reindex(brain=None,
                o=None):
        """
        """
        if o is None:  # Normalfall
            if brain is None:
                raise ValueError('neither brain nor o(bject) given!')
            try:
                o = brain.getObject()
            except KeyError as e:
                logger.error('KeyError %(e)r for brain %(brain)r', locals())
            except Exception as e:
                logger.error('brain %(brain)r: unexpected exception!',
                             locals())
                logger.exception(e)
            if o is None:
                logger.error("brain %(brain)r: zombie brain?",
                             locals())
                return False
        elif brain is not None:
            o2 = brain.getObject()
            if o2 is not o:
                logger.error("brain %(brain)r doesn't match object %(o)r",
                             locals())
                return False

        if debug:
            pp('*** Object %(o)r found!' % locals())
            set_trace()

        try:
            catalog_reindex(o, **ri_kwargs)
        except POSKeyError as e:
            logger.error('error reindexing %(o)r: %(e)r', locals())
            return False
        except Exception as e:
            logger.error('error reindexing %(o)r: %(e)r', locals())
            raise
        else:
            if return_brain:
                uid = o.UID()
                brains = get_brain(UID=uid)
                if not brains:
                    logger.error('No brains for object %(o)r, uid=%(uid)r!',
                                 locals())
                    return None
                elif brains[1:]:
                    num = len(brains)
                    logger.error('Multiple brains for object %(o)r, uid=%(uid)r (%(num)d)!',
                                 locals())
                    return None
                else:
                    return brains[0]
            return True

    return reindex


def make_query_extractor(context, do_pop=True):
    def extract_query(dic):
        """
        Extrahiere die bekannten Query-Argumente für die Katalogsuche
        und gib den Extrakt zurück
        """
        query = {}
        if do_pop:
            pop = dic.pop
        else:
            pop = dic.get

        if 'getExcludeFromSearch' not in dic:
            query['getExcludeFromSearch'] = False
        else:
            val = pop('getExcludeFromSearch')
            if val is not None:
                query['getExcludeFromSearch'] = int(val)
        # optionale Argumente ohne Vorgabewert:
        for name in [
            'portal_type',
            'getCustomSearch',
            'path',
            ]:
            if name in dic:
                val = pop(name)
                if isinstance(val, basestring):
                    val = [val]
                query[name] = val
        # Vorgabe: alle aktiven Sprachen
        Language = pop('Language', None)
        if Language is None:
            Language = getAllLanguages(context)
        # https://docs.plone.org/develop/plone/searching_and_indexing/query.html#bypassing-language-check:
        if isinstance(Language, basestring) and Language != 'all':
            Language = [Language]
        query['Language'] = Language
        return query
    return extract_query


def reindex_all(**kwargs):
    """
    Reindiziert die angegebenen Objekte
    """
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('reindex')
    catalog = kwargs.pop('catalog', None)
    if catalog is None:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    limit = kwargs.pop('limit', None)
    ri_kwargs = {'catalog': catalog,
                 'logger': logger,
                 }
    for name in [
        'idxs',
        'update_metadata',
        ]:
        if name in kwargs:
            ri_kwargs[name] = kwargs.pop(name)

    from pdb import set_trace; set_trace()
    extract_query = make_query_extractor(context)
    query = extract_query(kwargs)
    portal_types = query.pop('portal_type')
    Language = query.pop('Language')
    if kwargs:
        logger.error('Unused keyword arguments: %(kwargs)s', locals())
    logger.info('reindex_all: query args are:\n  %s',
                '\n  '.join(['%r=%r' % tup
                             for tup in query.items()
                             ]))

    i = 0
    reindex = make_reindexer(**ri_kwargs)
    transaction.begin()
    try:
        for pt in portal_types:
            for la in Language:
                q = {'portal_type': pt,
                     'Language': la,
                     }
                q.update(query)
                ii = 0
                for brain in catalog(q):
                    if not ii:
                        logger.info('portal_type=%(pt)r, Language=%(la)r ...',
                                    locals())
                    ii += 1
                    if reindex(brain):
                        i += 1
                        if not i % 100:
                            logger.info('committing after %(i)r. change', locals())
                            transaction.commit()
                        if limit is not None and i >= limit:
                            return bool(i)
        return bool(i)
    finally:
        if i % 100:
            logger.info('committing remaining changes; total: %(i)r', locals())
            transaction.commit()


def iterate_query(func, **kwargs):
    """
    func -- eine Funktion, die ein Katalogobjekt entgegennimmt und einen
            Wahrheitswert zurückgibt
    limit -- um die Bearbeitung auf <N> Objekte zu beschränken (zur
             Entwicklung)
    period -- wenn eine Zahl übergeben, werden die Änderungen nach je <period>
              Änderungen gesichert
    logger, catalog, context -- wie üblich; context wird jedenfalls benötigt

    sonstige benannte Argumente werden an --> make_query_extractor(context)
    übergeben
    """
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('reindex')
    catalog = kwargs.pop('catalog', None)
    if catalog is None:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    limit = kwargs.pop('limit', None)
    period = kwargs.pop('period', None) or None

    extract_query = make_query_extractor(context)
    query = extract_query(kwargs)
    logger.info('iterate_query: query args are:\n  %s',
                '\n  '.join(['%r=%r' % tup
                             for tup in query.items()
                             ]))
    i = 0
    if period is not None:
        transaction.begin()
    try:
        for brain in catalog(query):
            if func(brain):
                i += 1
                if limit is not None and i >= limit:
                    break
                if period is None:
                    continue
                if not i % period:
                    logger.info('committing after %(i)r changes', locals())
                    transaction.commit()
    finally:
        if (period is not None and
            i % period
            ):
            logger.info('final commit after %(i)r changes', locals())
            transaction.commit()


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


def make_mover(context=None, **kwargs):
    """
    Erzeuge eine Funktion, die Seiten verschiebt und/oder UIDs zuweist.
    Benötigt werden hierzu
    - der Portalkatalog
    - das Portal und seine ID
    Die übliche Vorgehensweise:
    1. Wenn eine UID übergeben wurde, suche nach dieser UID.
       Wenn das Objekt über diese UID gefunden wurde, muß es einen der
       aufgeführten Pfade haben (den neuen oder, sofern angegeben, einen der
       alten); ansonsten tritt ein Fehler auf.
       Wenn die UID keinen Treffer ergab, suche an den angegebenen Stellen (neu
       und ggf. alt):
       - wenn nichts gefunden, erstelle ein neues Objekt an der *neuen* Stelle;
       - wenn an einer alten Stelle gefunden, verschiebe das Objekt;
       - weise dem neuen, vorhandenen oder verschobenen Objekt die UID zu.
    """

ACCEPT_ANY = (0, 'ACCEPT ANY')
def make_renamer(**kwargs):
    """
    Erzeuge eine Funktion, die ein per UID angegebenes Objekt umbenennt;
    Voraussetzung: der Elternordner bleibt derselbe (also keine Verschiebung)
    """
    if 'catalog' not in kwargs:
        context = kwargs.pop('context')
        catalog = getToolByName(context, 'portal_catalog')
    else:
        catalog = kwargs.pop('catalog')
    logger = kwargs.pop('logger')
    verbose = kwargs.pop('verbose', False)
    get_object = kwargs.pop('get_object', False)

    def rename_object(uid=None, oldid=None, newid=None,
                      verbose=verbose,
                      get_object=get_object,
                      **kwargs):
        """
        For historical reasons, the 1st three arguments are uid, oldid,
        newid; now they are all technically optional ...

        Thus, please specify all options by name:

          o -- the object to change.
          brain -- a catalog brain pointing to o.
                   If both are given, brain.getObject() must be identical
                   to o.
          uid -- if neither o nor brain is given, uid is required

        Changes and constraints:

          oldid -- constrain the ID of the object to be renamed;
                   None (default) or (more explicit) ACCEPT_ANY to skip
                   this check
          newid -- the new ID. If None, or if the same as the current id,
                   no renaming is performed

          newtitle -- a new value for the title
          oldtitles -- a list of possible old values for the title.

          The function expects to get at least a newid or newtitle;
          if neither is given, a TypeError is raised.

        Other options:

          verbose -- be a little bit more verbose, especially for skipped
                     operations
          get_object -- always compute (if not given) the object, even if
                        not necessary for internal processing
                        (because no changes are applicable).
                        If not specified, the return value might be None.
        """
        o = kwargs.pop('o', None)
        brain = kwargs.pop('brain', None)
        spec = None  # how was the object specified?
        if o is None:
            if brain is None:
                if uid is None:
                    raise ValueError('One of uid, brain or o(bject) '
                                     'is required!')
                spec = 'UID %(uid)r' % locals()
                query = {'UID': uid}
                brains = catalog(query)
                if not brains:
                    raise ValueError('UID %(UID)r not found!', query)
                elif brains[1:]:
                    number = len(brains)
                    raise ValueError('%(spec)s: Too many hits! (%(number)d)'
                                     % locals())
                brain = brains[0]
            if get_object:
                o = brain.getObject()
                if spec is None:
                    spec = repr(o)
            if spec is None:
                spec = 'brain(%s)' % (brain.getPath,)
        elif brain is not None:
            o2 = brain.getObject()
            if o2 is not o:
                raise ValueError('Given brain for %(o2)r doesn\'t match '
                                 'the given object %(o)r!'
                                 % locals())
            spec = repr(o)

        oldtitles  = kwargs.pop('oldtitles', None) or []
        newtitle = kwargs.pop('newtitle', None)

        if kwargs:
            logger.error('%(spec)s: ignored arguments %(kwargs)r!', locals())

        if not newid and not newtitle:
            raise TypeError('%(spec)s: No new id, no new title; nothing to do!'
                             % locals())

        changes = 0
        try:
            # we do have at least either o or a brain 
            assert o is not None or brain is not None

            if newtitle:
                if brain is not None:
                    title = brain.Title
                else:
                    title = o.title()
                if title == newtitle:
                    if verbose:
                        if o is None: o = brain.getObject()
                        logger.info('%(spec)s: New title %(newtitle)r already set',
                                    locals())
                else:
                    if oldtitles == ACCEPT_ANY or title in oldtitles:
                        if o is None: o = brain.getObject()
                        logger.info('%(spec)s: setting title to %(newtitle)r '
                                    '(old: %(title)r)',
                                    locals())
                        o.title = newtitle
                        changes += 1
                    else:
                        logger.error('%(spec)s: unexpected title %(title)r!',
                                     locals())

            if not newid:
                if verbose:
                    logger.info('%(spec)s: No ID change', locals())
            else:
                if brain is not None:
                    current_id = brain.getId
                else:
                    current_id = o.getId()
                if current_id == newid:
                    if verbose:
                        logger.info('%(spec)s: renaming to %(newid)r already done.',
                                    locals())
                elif current_id == oldid or oldid in (None, ACCEPT_ANY):
                    if o is None: o = brain.getObject()
                    ## when renaming, we need to refresh any child nodes:
                    #if brain is not None:
                    #    oldpath = brain.getPath
                    #else:
                    #    oldpath = o.getPath()
                    parent = o.aq_parent
                    logger.info('%(spec)s: renaming'
                                ' from %(current_id)r to %(newid)r.',
                                locals())
                    parent.manage_renameObject(oldid, newid)
                    o = getattr(parent, newid)
                    changes += 1
                    if verbose:
                        logger.info('renaming of %(current_id)r to %(newid)r done.', locals())
                else:
                    logger.error('%(spec)s: unexpected ID %(current_id)r, skipping.', locals())
        except Exception as e:
            logger.error('%(spec)s: renaming of %(current_id)r to %(newid)r failed!\n%(e)r', locals())
            raise
        else:
            if changes:
                assert o is not None, ('We have changes, so we need to '
                                       'have had the object!')
                logger.info('%(spec)s: reindexing ...', locals())
                o.reindexObject()
        return o

    return rename_object


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


def setVersionedTypes(portal, additional_types, logger=None):
    """
    Füge die übergebenen Typen (portal_type) der Änderungsverfolgung hinzu

    Achtung: um eine nützliche diff-Ausgabe zu erhalten, muß für jeden
    betroffenen Typ ein Diff-Tool konfiguriert sein! (siehe ../diff_tool.xml)
    """
    # siehe:
    # - http://www.uwosh.edu/ploneprojects/docs/how-tos/how-to-enable-versioning-history-tab-for-a-custom-content-type/
    # - https://docs.plone.org/4/en/manage/upgrading/version_specific_migration/p40_to_p41_upgrade.html#id7

    if logger is None:
        logger = logging.getLogger('setVersionedTypes')

    portal_repository = getToolByName(portal, 'portal_repository')
    old_policies = portal_repository.getPolicyMap()
    versionable_types = list(portal_repository.getVersionableContentTypes())
    for type_id in additional_types:
        if type_id not in versionable_types:
            logger.info('adding %(type_id)r to versionable types ...', locals())
            versionable_types.append(type_id)
        else:
            policies = old_policies.get(type_id, None)
            logger.info('versioning policies for %(type_id)r: %(policies)r', locals())

    logger.info('saving additions ...')
    portal_repository.setVersionableContentTypes(versionable_types)


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

    site = getToolByName(context, 'portal_url')

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
        if isinstance(path, basestring):
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
    extract - eine Funktion, die aus dem (ggf. durch die tranform-Funktion
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
            if isinstance(text, unicode):
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
            if isinstance(text, unicode):
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
                pp(ppargs)
                set_trace()
            collect_uids_2(getbyuid(uid), depth+1, stack+[uid])

    return collect_uids_2, theset


def make_simple_localroles_function(**kwargs):
    """
    Erzeuge eine einfache Funktion, um (hier: ohne Differenzierung nach
    portal_type ö.ä.) für alle Objekte mit dem angegeben Workflow-Zielstatus
    <target_state> die lokalen Rollen <roles> für den Prinzipal <userid>
    zuzuweisen; die Funktion set_local_roles wird dies dann so interpretieren,
    daß etwaige schon vorhandene weitere lokale Rollen erhalten bleiben.
    """
    for_target_state = kwargs.pop('target_state', 'restricted')
    userid = kwargs.pop('userid')
    roles = kwargs.pop('roles')
    add = kwargs.pop('add', True)
    if isinstance(roles, basestring):
        roles = [roles]
    def new_local_roles(brain, target_state):
        if target_state == for_target_state:
            return [(userid, roles, add)]
        return []
    return new_local_roles


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
            isinstance(thelist, basestring)
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


def extract_object_or_brain(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (o, brain) zurück.

    Der Zweck ist die Ermittlung des Objekts; wenn 'brain' nicht enthalten ist,
    wird hierfür None zurückgegeben.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
        if o is None:
            o = brain.getObject()
    else:
        o = get('o')
        brain = None
    return o, brain


def extract_object_and_brain(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (o, brain) zurück.

    Das jeweils fehlende wird ermittelt; eines von beiden muß natürlich
    enthalten sein.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
        if o is None:
            o = brain.getObject()
    else:
        o = get('o')
        brain = None
    if brain is None:
        brain = o.getHereAsBrain()
    return o, brain


def extract_brain_or_object(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (brain, o) zurück.

    Der Zweck ist die Ermittlung des 'Brains'; wenn 'o' nicht enthalten ist,
    wird hierfür None zurückgegeben.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
    else:
        o = get('o')
        brain = None
    if brain is None:
        brain = o.getHereAsBrain()
    return brain, o


def set_local_roles(**kwargs):
    """
    Modifiziere die lokalen Rollenzuweisungen des übergebenen Objekts

    Argumente, alle benannt zu übergeben:

    o -- das Objekt
    brain -- dessen Indexobjekt
             (eines der beiden muß angegeben werden)

    logger -- der Logger

    func -- Eine Funktion, die aus <brain> und <target_state> eine Liste mit
            den gewünschten Änderungen ermittelt (wie <thelist>);
            siehe make_simple_localroles_function
    target_state -- nur zur Übergabe an <func>

    thelist -- eine Liste von (userid, roles [, add])-Tupeln;
               nur benötigt (und verwendet), wenn <func> nicht angegeben

    Von diesen wird zwingend benötigt:
    - logger
    - mindestens eines von o und brain
      (keine explizite Prüfung; es wird aber ggf. ein Fehler auftreten)
    - alternativ:
      - func und target_state, um die zu setzenden oder zu löschenden
        Rollen mit Hilfe der Funktion <func> zu ermitteln;
        oder:
      - thelist
        (derzeit ignoriert, wenn <func> übergeben wurde und nicht None ist)
    """
    o, brain = extract_object_and_brain(kwargs)
    # if 'func' in kwargs:
    func = kwargs.pop('func', None)
    if func is not None:
        # wird benötigt, als Argument für die Funktion! 
        target_state = kwargs.pop('target_state')
        thelist = func(brain, target_state)
    else:
        thelist = kwargs.pop('thelist')
    logger = kwargs.pop('logger')
    if not thelist:
        return False
    uid = brain.UID
    changes = 0
    def set_of_roles(userid):
        return set(o.get_local_roles_for_userid(userid=userid))

    roles_of_user = Proxy(set_of_roles)
    changed_users = set()
    for tup in thelist:
        userid, roles = tup[:2]
        if isinstance(roles, basestring):
            roles = [roles]
        if tup[2:]:
            tail = tup[3:]
            if tail:
                logger.warn('set_local_roles: %(tup)r is too long'
                            '; ignoring %(tail)r',
                            locals())
            add = tup[2]
            if add not in (True, False,
                           1, 0,  # pep 20.2
                           ):
                txt = ('set_local_roles: %(tup)r contains wrong 3rd value'
                       ' %(add)r; boolean expected'
                       ) % locals()
                logger.error(txt)
                raise ValueError(txt)
        else:
            add = True

        for role in roles:
            roles_set = roles_of_user[userid]
            if role in roles_set:
                if add:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' %(role)r already found (%(o)r)', locals())
                else:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' removing %(role)r (%(o)r)', locals())
                    roles_set.discard(role)
                    changed_users.add(userid)
            else:
                if add:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' adding %(role)r (%(o)r)', locals())
                    changed_users.add(userid)
                    roles_set.add(role)
                else:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' %(role)r not found (%(o)r)', locals())

    if not changed_users:
        return False
    done_users = set()
    for userid in sorted(changed_users):
        roles_set = roles_of_user[userid]
        if roles_set:
            sorted_roles = sorted(roles_set)
            logger.info('%(uid)r local roles for %(userid)r:'
                        ' set to %(sorted_roles)s (%(o)r)', locals())
            o.manage_setLocalRoles(userid, sorted_roles)
            done_users.add(userid)
    changed_users.difference_update(done_users)
    if changed_users:
        userids = sorted(changed_users)
        logger.info('%(uid)r local roles for %(userids)s:'
                    ' removing all roles (%(o)r)', locals())
        o.manage_delLocalRoles(userids)
    o.reindexObjectSecurity()
    return True


TRANSITIONS_MAP = {}
for from_state, to_state, tr in (
    ('restricted', 'visible',    'make_visible'),
    ('restricted', 'published',  'make_public'),
    ('visible',    'published',  'make_public'),
    ('visible',    'restricted', 'make_restricted_again'),
    ('published',  'visible',    'make_visible_again'),
    ('published',  'restricted', 'make_restricted_again'),
    # für Vortragsseiten, die in Demo-Kursen benötigt werden:
    ('inherit',    'visible',    'make_visible'),
    ('inherit',    'published',  'make_public'),
    # nichts zu tun, aber kein Fehler:
    ('restricted', 'restricted', None),
    ('visible',    'visible',    None),
    ('published',  'published',  None),
    ):
    TRANSITIONS_MAP[(from_state, to_state)] = tr
def make_transition_applicator(**kwargs):  # ---- [ m._t._a. ... [ -[[
    """
    Erzeuge eine Funktion, die den Workflow-Status eines als brain übergebenes
    Objekts ändert; dabei kann der Zielstatus aus der UID ermittelt werden
    (siehe uids_tuples).

    Argumente:
    - {default_,}target_state - der Zielstatus, wenn nicht aus uids_tuples zu
                                ermitteln
    - uids_tuples - eine Liste von (set, status, funktion)-Tupeln:
                    set - ein Set von UIDs, die den <status> (oder "besser")
                          erhalten sollen;
                    funktion - eine für die Objekte mit dem Zielstatus <status>
                               aufzurufende Funktion (z. B. zur rekursiven
                               Ermittlung der UIDs der verwendeten Objekte)
    - transitions_map - siehe TRANSITIONS_MAP
    - returns - was soll die Funktion zurückgeben?
      'changed' - True, wenn geändert wurde, sonst False (Vorgabewert)
      'target' - True, wenn der Zielstatus der gewünschte ist, sonst False
      'both' - ein 2-Tupel (changed, target)
      'error' - wie 'changed', aber mit Exception z. B. bei unbekannten
                Transitionen
    - doit_function - eine Funktion, die (nach den sonstigen Prüfungen)
                      entscheidet, ob die Transition (jetzt) angewendet werden
                      soll; sollte im anderen Fall eine Datenstruktur füllen,
                      um die (verzögerten) Transitionen später nachzuholen.
                      Signatur: f(brain, target_state)
    - set_inherit - soll die Akquisition von Zugriffsrechten vom Elternobjekt
                    umgeschaltet werden?  Mögliche Werte:
                    True - einschalten
                    False - ausschalten
                    'auto' - einschalten für Zielstatus 'inherit' oder
                             'published', sonst ausschalten
                    'autorestrict' - wie 'auto',
                                     aber nichts tun für 'published' (Vorgabe)
                    None - nichts tun
                    Die etwaige Umschaltung wird ungeachtet des Ergebnisses
                    einer <doit_function> ausgeführt, nicht aber wenn die
                    Transition lt. der internen <done_sets> (Schlüssel:
                    Zielstatus) schon durchgeführt wurde.
    - localroles_function - insbesondere wichtig für den Zielstatus
                    'restricted': eine Funktion, die bestimmt,
                    - welche "Prinzipale" (hier i.d.R.: Gruppen)
                    - welche lokalen Rollen
                    - zugewiesen (Vorgabe) oder entzogen bekommen sollen;
                    Signatur: f(brain, target_state).
                    Als Rückgabewert wird eine Liste von (id, [Rolle,...],
                    add)-Tupeln erwartet;
                    siehe --> make_simple_localroles_function
    - set_best_status - soll für das jeweilige Objekt der "beste" Status
                        gesetzt, d.h. ein etwaiger done-Vermerk für einen
                        nachgeordneten Status ignoriert werden?
                        (Siehe DictOfSets und die durch <uids_tuples>
                        vorgegebene Reihenfolge)
                        Vorgabe: True, wenn <uids_tuples> übergeben und nicht
                        leer, ansonsten False
    - force - soll eine Transition durchgeführt werden, obwohl sie für das
              übergebene Katalogobjekt (Kriterium: UID) oder einen "besseren"
              (=öffentlicheren) Zielstatus bereits durchgeführt wurde?
              (verwendet internes Dict <done_sets>)
    - regard_current - soll eine Transition als erfolgreich betrachtet werden
                       (insbesondere incl. der <done_sets>), wenn (ungeachtet
                       etwaiger Fehler) das Ergebnis stimmt?
    - shortcircuit - Transition von vornherein nicht versuchen, wenn der
                     Zielstatus schon vorliegt. Kann viel Zeit sparen,
                     insbesondere bei Medien mit Vorschaubildern!

    Debugging-Optionen:

    - watched_uid_and_status - siehe --> make_watcher_function;
                     set_trace, wenn apply_transition sich anschickt, das
                     Objekt mit der UID <uid> auf <status> zu setzen
    - tell_about_uids - ein Dict, {<uid>: <label>, ...},
                        oder eine Liste [(<uid>, <label>), ...];
                     wenn angegeben, wird zusätzlich eine Funktion
                     zurückgegeben, die über die Größen der internen Sets
                     informiert und darüber, ob die hier angegebenen UIDs
                     jeweils darin enthalten sind.
                 ACHTUNG:
                     Der Rückgabewert ist dann also keine einzelne Funktion,
                     sondern ein 2-Tupel (<apply_transition>, <tell...>)!
    """
    # ]]------ [ make_transition_applicator: Argumente ... [
    status_set = defaultdict(set)
    target_sets = DictOfSets()
    status_func = {}
    # Behandlung schon erledigter ...
    done_sets = DictOfSets()
    force = kwargs.pop('force', False)
    shortcircuit = kwargs.pop('shortcircuit', True)

    regard_current = kwargs.pop('regard_current', True)
    if 'default_target_state' in kwargs:
        default_target_state = kwargs.pop('default_target_state')
    else:
        default_target_state = kwargs.pop('target_state', None)
    uids_tuples = kwargs.pop('uids_tuples')
    for tup in uids_tuples:
        theset, target_state, func = tup
        if target_state in done_sets:
            raise ValueError('duplicate status %(target_state)r!' % locals())
        elif not isinstance(target_state, basestring):
            raise ValueError('Workflow status expected! (%target_state()r)'
                             % locals())
        target_sets.add_set(target_state)
        done_sets.add_set(target_state)
        if theset is None:
            if default_target_state is None:
                raise ValueError('No set for %(target_state)r,'
                                 ' and no default_target_state!'
                                 % locals())
            elif target_state != default_target_state:
                raise ValueError('No set for %(target_state)r which doesn\'t match'
                                 ' default_target_state %(default_target_state)r!'
                                 % locals())
            else:
                theset = set()
        elif not isinstance(theset, set):
            theset = set(theset)
        status_set[target_state] = theset
        target_sets[target_state].update(theset)
        status_func[target_state] = func
    set_best_status = kwargs.pop('set_best_status', bool(uids_tuples))
    del uids_tuples
    # neue UIDs den target_sets nur hinzufügen, wenn der Zielstatus
    # in den ursprünglich angegebenen enthalten ist: 
    target_values = target_sets.ordered_keys()
    transitions_map = kwargs.pop('transitions_map', TRANSITIONS_MAP)
    returns = kwargs.pop('returns', 'changed')
    r_pool = 'changed target both error'.split()
    if returns not in r_pool:
        raise ValueError('invalid "returns" value (%(returns)r); '
                         'one of %(r_pool)s expected'
                         % locals())
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('apply_transition')

    verbosity = kwargs.pop('verbosity', 1)

    doit_function = kwargs.pop('doit_function', None)
    if doit_function is not None:
        doit = None
    else:
        doit = kwargs.pop('doit', True)
        if doit not in (False, True):
            raise ValueError('invalid "doit" value (%(doit)r)'
                             % locals())

    # ---------------------- [ Lokale Rollen ... [
    set_inherit = kwargs.pop('set_inherit', 'autorestrict')
    if set_inherit is None:
        pass
    elif set_inherit not in (False, True, 'auto', 'autorestrict'):
        raise ValueError('invalid "set_inherit" value (%(set_inherit)r)'
                         % locals())
    localroles_function = kwargs.pop('localroles_function', None)
    # ---------------------- ] ... Lokale Rollen ]

    # ---------- [ für Debugging (set_trace) ... [
    if 'watched_uid_and_status' in kwargs:
        tup = kwargs.pop('watched_uid_and_status')
        if tup:
            watched_case = make_watcher_function(tup,
                                                 logger=logger,
                                                 msg='WATCHED CASE: uid = %(key)r'
                                                 ' --> status = %(val)r!')
            logger.warn('DEBUGGING: set_trace, wenn ein beobachteter Fall '
                        'eintritt!')
        else:
            watched_case = gimme_False
    else:
        watched_case = gimme_False
    # ---------- ] ... für Debugging (set_trace) ]
    # -------- ] ... make_transition_applicator: Argumente ]

    tell_about_uids = kwargs.pop('tell_about_uids', False)
    if tell_about_uids:
        if isinstance(tell_about_uids, dict):
            tell_about_uids = tell_about_uids.items()
    
    # ------------ [ m._t._a.: generierte Infofunktion ... [
    stored_hits = {'prev': None,
                   'current': [],
                   }
    def summary(label=''):
        """
        Gib eine Zusammenfassung aus;
        lies hierzu folgende Variablen aus der Closure:

        done_sets -- die Sets mit den Erledigungen
        target_sets -- die Sets mit den gefundenen (oder explizit angegebenen)
                       UIDs
        stored_hits -- ...
        """
        info = []
        if label:
            label = label.strip()
        elif label is None:
            label = ''
        if label:
            label = label.join((' (', ')'))

        current_hits = stored_hits['current']
        has_hits = False
        found_targets = False
        for title, dos in [   # DictOfSets
            ('Zielstatus-Sets', target_sets),
            ('DONE-Sets',       done_sets),
            ]:
            if len(dos):
                info.append(title)
                for status in dos.ordered_keys():
                    theset = dos[status]
                    contains = []
                    for key, txt in tell_about_uids:
                        if key in theset:
                            current_hits.append((key, status, 'done'))
                            if key != txt:
                                contains.append('%(txt)s (%(key)s)' % locals())
                            else:
                                contains.append(key)
                    L = len(theset)
                    line = '%(L)7d %(status)r' % locals()
                    if contains:
                        has_hits = True
                        line += '; contains '+ ', '.join(contains)
                    info.append(line)
        if info:
            info.insert(0, '')
            info.append('')
        else:
            info.append('<empty!>')
        logger.info('apply_transition: SUMMARY%s {{%s}}',
                    label,
                    '\n  '.join(info))
        prev_hits = stored_hits['prev']
        if prev_hits is None:
            res = has_hits
        else:
            res = current_hits != prev_hits
        stored_hits['prev'] = current_hits
        stored_hits['current'] = []
        return res
    # ------------ ] ... m._t._a.: generierte Infofunktion ]

    # --------- [ m._t._a.: generierte Arbeitsfunktion ... [
    def apply_transition(brain, target_state=None,
                         default_target_state=default_target_state,
                         doit=doit,
                         logger=logger,
                         verbosity=verbosity,
                         force=force,
                         regard_current=regard_current,
                         set_inherit=set_inherit,
                         set_best_status=set_best_status,
                         localroles_function=localroles_function,
                         shortcircuit=shortcircuit):
        """
        Wende eine Workflow-Transition an und gib einen oder mehrere
        Wahrheitswerte zurück (--> erzeugende Funktion, <returns>)

        brain - das jeweilige Objekt wird als Katalogobjekt erwartet!
        target_state - wenn None, werden zunächst die Sets aus der erzeugenden
                       Funktion durchsucht (--> uid_tuples)
        default_target_state - verwendet, wenn <target_state> nach etwaiger
                       Suche in den <uid_tuples> immer noch None
        doit - wenn None, wird die <doit_function> (siehe erzeugende Funktion)
               verwendet, um zu entscheiden, ob die Transition direkt
               durchgeführt werden soll, oder andernfalls das Objekt für die
               spätere Verarbeitung vorzumerken
        logger - der zu verwendende Logger (Vorgabe aus erzeugender Funktion)
        verbosity - Ausführlichkeit, dto.
        force - <done_sets> ignorieren (siehe erzeugende Funktion)
        regard_current - wenn der aktuelle schon dem Zielstatus entspricht,
                         dies auch im Fehlerfall als erfolgreich behandeln;
                         weitgehend obsolet durch --> shortcircuit
        set_inherit - ein Wahrheitswert oder 'auto{,restrict}', oder None.
                      Siehe oben.
                      Wenn None, wird die etwaige Akquisition lokaler Rollen
                      nicht modifiziert.
        set_best_status - Vorgabewert siehe oben
        shortcircuit - wenn der aktuelle schon dem Zielstatus entspricht,
                       die Aktion als erfolgreich durchgeführt betrachten
                       (wenn auch ohne Änderungen)
        """
        # TODO: add_viewers_group, für restricted:
        # - auch, wenn Status schon 'restricted' ist (Reparatur)
        # - abhängig z. B. von portal_type; also z. B. durch Funktion zu regeln 
        current_state = brain.review_state
        changed = False
        target_ok = True
        done = False
        o = None
        uid = brain.UID
        if target_state is None:
            target_state = target_sets.first_hit(uid, default_target_state)
            if target_state is None:
                target_state = default_target_state
                if watched_case(uid, target_state):
                    set_trace()
            if target_state is None:
                logger.error('Unknown target_state for UID %(uid)r', locals())
                if returns == 'error':
                    raise ValueError('Unknown target_state for UID %(uid)r'
                                     % locals())
                else:
                    changed, target_ok = None, None
                    done = True
        else:
            if watched_case(uid, target_state):
                set_trace()
            if target_state in target_values:
                # Zielstatus wurde übergeben; dem korrekten Set hinzufügen:
                target_sets[target_state].add(uid)

        # ----------------------- [ Zielstatus bekannt ... [
        if (not done   # der Regelfall!
                       # der Zielstatus wurde übergeben,
                       # konnte aus einem der Sets ermittelt werden,
                       # oder es gab zumindest einen Vorgabewert:
            and target_state is not None
            ):
            o = brain.getObject()
            # Es werden die Statuus geordnet überprüft;
            # was schon auf 'published' gesetzt wurde, braucht für 'published',
            # 'visible' und etwaige weitere nicht mehr berücksichtigt zu
            # werden.
            if set_best_status:
                done_state = done_sets.first_hit(uid, target_state)
            else:
                done_state = done_sets.first_hit(uid)
            if done_state is not None:
                logger.info('UID %(uid)r (--> %(target_state)r)'
                            ' found as done for %(done_state)r',
                            locals())
                if not force:
                    done = True  # set_inherit ist davon unabhängig

            # ---- [ nicht erledigt lt. done-Sets ... [
            if not done:
                func = status_func.get(target_state, None)
                if func is not None:
                    func(brain)  # z. B. rekursive Ermittlung der UIDs!
                if doit is None:
                    doit = doit_function(brain, target_state) or False
                if doit and shortcircuit:
                    if current_state == target_state:
                        changed, target_ok = False, True
                        done_sets.add(uid, target_state)
                        doit = False
                        pt = brain.portal_type
                        logger.info('%(uid)r %(pt)r (%(current_state)r): '
                                    'Keine Aktion erforderlich',
                                    locals())
                transition = None
                if doit:
                    # nun die Transition ermitteln:
                    try:
                        transition = TRANSITIONS_MAP[(current_state, target_state)]
                    except KeyError:
                        if regard_current and (current_state == target_state):
                            logger.info('%(o)r: keine Transition %(current_state)r --> %(target_state)r,'
                                        'aber der Zielstatus stimmt schon',
                                         locals())
                            changed, target_ok = None, True
                            done_sets.add(uid, target_state)
                        else:
                            logger.error('%(o)r: keine Transition %(current_state)r --> %(target_state)r bekannt!',
                                         locals())
                            if returns == 'error':
                                raise
                            else:
                                changed, target_ok = None, current_state == target_state
            # ---- ] ... nicht erledigt lt. done-Sets ]
            if not done and transition is None:
                if verbosity >= 3:
                    logger.info('Objekt %(uid)r bleibt %(current_state)r', locals())
                changed, target_ok = False, current_state == target_state
                done = True
            # --------- [ <transition> ist nun gesetzt ... [
            if not done:  # transition hat jetzt einen verwendbaren Wert
                # --------------- [ WF-Transition ... [
                if doit is None:
                    doit = doit_function(brain, target_state)
                if doit:
                    if o is None:
                        o = brain.getObject()
                    if verbosity >= 2 or brain.portal_type == 'Folder':
                        logger.info('%(uid)r %(o)r (%(current_state)r):'
                                    ' %(transition)s) ...',
                                    locals())
                    wft = getToolByName(o, 'portal_workflow')
                    try:
                        res = wft.doActionFor(o, transition)
                    except WorkflowException as e:
                        if regard_current and (current_state == target_state):
                            logger.info('%(uid)r, Transition fehlgeschlagen,'
                                        'aber der Zielstatus %(target_state)r stimmt schon (%(o)r)',
                                         locals())
                            target_ok = True
                            done_sets.add(uid, target_state)
                        else:
                            logger.error('%(uid)r %(o)r, Transition %(transition)r: %(e)r',
                                         locals())
                            target_ok = False
                    else:
                        done_sets.add(uid, target_state)
                        if verbosity >= 1:
                            logger.info('%(uid)r %(o)r, %(transition)s: OK', locals())
                        changed, target_ok = True, True
                else:
                    o = None
                    changed, target_ok = None, False
                # --------------- ] ... WF-Transition ]
            # --- [ Berechtigungs-Akquisition ... [ 
            if set_inherit is not None:
                if set_inherit == 'auto':
                    set_inherit = target_state in ('published', 'inherit')
                elif set_inherit == 'autorestrict':
                    if target_state in ('published',):
                        set_inherit = None
                    elif target_state == 'inherit':
                        set_inherit = True
                    else:
                        set_inherit = False
                if set_inherit is not None:
                    if o is None:
                        o = brain.getObject()
                    sharing = o.restrictedTraverse('@@sharing')
                    act_ = set_inherit and 'activate' or 'deactivate'
                    logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                '%(act_)s permission inheritance ...',
                                locals())
                    if sharing.update_inherit(set_inherit):
                        changed = True
                        logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                    'permission inheritance %(act_)sd',
                                    locals())
                    elif verbosity >= 1:
                        logger.info('%(uid)r %(o)r (-> %(target_state)r): '
                                    'permission inheritance not changed',
                                    locals())
            # --- ] ... Berechtigungs-Akquisition ]
            if localroles_function is not None:
                if set_local_roles(brain=brain, o=o,
                                   func=localroles_function,
                                   target_state=target_state,
                                   logger=logger):
                    changed = True
            # ---- ] ... <transition> ist nun gesetzt ]
        # ----------------------- ] ... Zielstatus bekannt ]

        if returns == 'target':
            return target_ok
        elif returns == 'both':
            return changed, target_ok
        else:  # 'changed' oder 'error'
            return changed
    # --------- ] ... m._t._a.: generierte Arbeitsfunktion ]

    if tell_about_uids:
        return apply_transition, summary
    return apply_transition
    # ----------------------------- ] ... make_transition_applicator ]


def getAllLanguages(context, exclude=[]):
    """
    Zur Suche nach allen Sprachen (Index: "Language"),
    um keine Objekte zu verfehlen
    """
    getAdapter = context.getAdapter
    langs = sorted([x[0] for x in getAdapter('pl')().listSupportedLanguages()])
    if '' not in langs:
        langs.append('')
    if exclude:
        exclude = set(exclude)
        unknown = exclude.difference(langs)
        if unknown:
            raise ValueError("Can't exclude unknown language codes %s!",
                             sorted(unknown))
        langs = set(langs)
        langs.difference_update(exclude)
        if not langs:
            raise ValueError('Excluding %s, nothing remains!',
                             sorted(exclude))
    return sorted(langs)


def step(func):
    """
    Dekorator für Migrationsschritte:
    - ergänzt ggf. fehlendes logger-Argument
    - stoppt die Zeit
    - (experimentell:)
      erlaubt das Weiterlaufen der Zope-Instanz auch nach manuellem Abbruch
      des Migrationsschritts
    """
    # da die def-Anweisung hier nicht ausgeführt wird, ist eine implizite
    # "Impfung" der verpackten Funktion mit zusätzlichen Variablen (wie z.B.
    # "site") leider nicht möglich; dafür würden zustäzliche Argumente
    # benötigt, und mithin eine Änderung der Signatur.

    @wraps(func)
    def wrapper(context, logger=None):
        funcname = func.__name__
        if logger is None:
            logger = logging.getLogger('setup:'+funcname)
        _started = time()
        try:
            res = func(context, logger)
        except Exception as e:
            delta = time() - _started
            if isinstance(e, KeyboardInterrupt):
                logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                             locals())
                logger.exception(e)
                raise StepAborted
            else:
                logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                             locals())
                logger.exception(e)
                raise
        else:
            delta = time() - _started
            logger.info('%(res)r <-- %(funcname)s (%(delta)5.2f seconds)', locals())
        return res

    return wrapper


def upgrade_step(destination, **kwargs):
    """
    Gib einen Dekorator zur einmaligen Verwendung zurück.
    Es wird als erstes Argument die Zielversion (destination)
    angegeben; weitere werden üblicherweise in einem Dict gesammelt:

    >>> deco_kwargs = {'package': __package__, 'module': __name__}
    >>> @upgrade_step(1001, **deco_kwargs)
    ... def create_interesting_folder(context, logger):
    ...     pass

    Der Dekorator sorgt für das (je nach Aufruf fehlende) logger-Argument;
    protokolliert wird:
    - die Zielversion (destination)
    - der Name der Funktion
    - jeweils wenn übergeben:
      - der Name des Python-Packages (package)
      - der Name des Moduls (module)
      - die Revisionsnummer (rev), normalerweise als String

    Die Logik ist wie folgt:
    - upgrade_step wird aufgerufen und verarbeitet die übergebenen Argumente,
      um eine Funktion mit einem Argument <func> zu erzeugen,
      die die übergebene Funktion dekoriert
    - die so generierte Funktion bekommt die letztlich zu dekorierende Funktion
      übergeben und gibt eine Wrapper-Funktion zurück, die folgendes tut:
      - sie erzeugt einen Logger, falls nicht übergeben,
        und ergänzt so das an die dekorierte Funktion übergebene logger-Argument;
      - sie protokolliert das Paket (sofern package übergeben; dringend
        empfohlen!) und die Zielversion
      - sie protokolliert den Namen der dekorierten Funktion
      - sie ruft die dekorierte Funktion auf und merkt sich den Zeitpunkt
      - sie protokolliert den Rückgabewert und die Brutto-Laufzeit der
        dekorierten Funktion
        - im Fehlerfall werden entsprechende Informationen protokolliert
      - schließlich nochmals ein Protokolleintrag für das Paket und die
        Zielversion
    """

    def make_wrapper():
        """
        package = package
        destination = destination
        rev = rev
        """
        rev = kwargs.pop('rev', 0)
        package = kwargs.pop('package')
        module = kwargs.pop('module', None)
        logger = kwargs.pop('logger', None)
        logger_name = kwargs.pop('logger_name', 'setup:%(funcname)s')

        @wraps(func)
        def wrapper(context, logger=logger):
            funcname = func.__name__
            package = package
            destination = destination
            rev = rev
            if logger is None:
                logger = logging.getLogger(logger_name % locals())
            logger.info('[ updating %(package)s to version %(destination)s ... [',
                        locals())
            '''            
                        {'package': package,
                         'destination': destination,
                        })
            '''            
            _started = time()
            if rev:
                logger.info('%(funcname)s@%(rev)s started', locals())
            else:
                logger.info('%(funcname)s started', locals())
            try:
                res = func(context, logger)
            except Exception as e:
                delta = time() - _started
                if isinstance(e, KeyboardInterrupt):
                    logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    logger.error('] ... update of %(package)s to version'
                                 ' %(destination)s aborted ]',
                                 locals())
                    raise StepAborted
                else:
                    logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    logger.error('] ... update of %(package)s to version'
                                 ' %(destination)s failed ]',
                                 locals())
                    raise
            else:
                delta = time() - _started
                logger.info('%(funcname)s completed (%(delta)5.2f seconds)', locals())
                logger.info('] ... %(package)s updated to version %(destination)s ]',
                            locals())
            return res

        return wrapper
    return make_wrapper()


def make_step_decorator(**kwargs):
    """
    Erzeuge einen Dekorator wie vorstehende Funktion --> step,
    aber ergänze bei der Protokollierung des Aufrufs, gemäß benannten
    Argumenten:
    - rev --> die svn-Revision des aufrufenden Moduls
    """
    rev = kwargs.pop('rev', 0)
    mask = 'setup:%(funcname)s'
    if rev:
        int(rev)
        mask += '@' + rev

    def make_wrapper(func, rev=rev):
        @wraps(func)
        def wrapper(context, logger=None):
            funcname = func.__name__
            rev = rev
            if logger is None:
                logger = logging.getLogger('setup:'+funcname)
            _started = time()
            if rev:
                logger.info('%(funcname)s@%(rev)s started', locals())
            try:
                res = func(context, logger)
            except Exception as e:
                delta = time() - _started
                if isinstance(e, KeyboardInterrupt):
                    logger.error('%(funcname)s aborted after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    raise StepAborted
                else:
                    logger.error('%(funcname)s: %(e)r after %(delta)5.2f seconds',
                                 locals())
                    logger.exception(e)
                    raise
            else:
                delta = time() - _started
                logger.info('%(funcname)s completed (%(delta)5.2f seconds)', locals())
            return res

        return wrapper
    return make_wrapper
