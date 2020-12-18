# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Python compatibility:
from __future__ import absolute_import

# Standard library:
import random
from collections import Counter, defaultdict
from copy import deepcopy
from functools import wraps
from posixpath import normpath
from string import capitalize
from time import time

# Zope:
import transaction
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.WorkflowCore import WorkflowException
# Exceptions:
from ZODB.POSException import POSKeyError

# Plone:
from plone.uuid.interfaces import IUUID

# visaplan:
from visaplan.tools.batches import batch_tuples
from visaplan.tools.classes import StackOfDicts
from visaplan.tools.minifuncs import gimme_False
from visaplan.tools.sequences import unique_union

# Local imports:
from visaplan.plone.tools._have import HAS_SUBPORTALS, HAS_VPSEARCH
from visaplan.plone.tools.setup._args import (
    _extract_move_args,
    apply_move_order_options,
    extract_layout_switch,
    normalize_menu_switch,
    setdefault_move_args,
    setdefault_source_language,
    )
from visaplan.plone.tools.setup._exc import \
    AlreadyTranslated  # from LinguaPlone, or a dummy
from visaplan.plone.tools.setup._exc import \
    CantAddTranslationReference  # ... enhanced information
from visaplan.plone.tools.setup._get_object import make_object_getter
from visaplan.plone.tools.setup._make_folder import make_subfolder_creator
from visaplan.plone.tools.setup._reindex import make_reindexer

if HAS_SUBPORTALS:
    # Local imports:
    from visaplan.plone.tools.setup._o_tools import (
        handle_subportal,
        might_set_subportal,
        )

if HAS_VPSEARCH:
    # Local imports:
    from visaplan.plone.tools.setup._o_tools import handle_united_search

# Logging / Debugging:
# Logging / Debugging:
import logging
from pdb import set_trace
from visaplan.tools.debug import pp

__all__ = [
        'clone_tree',  # sprachverknüpfter Verzeichnisbaum
        # internal:
        # '_clone_tree_inner'
        # '_move_objects'
        ]


def clone_tree(context, dic, **kwargs):  # --- [ clone_tree ... [
    """
    Erzeuge einen sprachverknüpften Klon

    Beispiel für dic: siehe visaplan.plone.structures.setupdata
    [JOURNAL_TREE, ELEARNING_TREE, KNOWHOW_TREE]

    Erforderliche Argumente:
    - context -- üblicherweise das Portalobjekt, oder ein anderes Objekt des
                 Objektbaums (um das Portalobjekt und die Tools zu beschaffen)
    - dic -- ein Python-Dict. mit Schlüssel für die Quellsprache und eine oder
             mehr Zielsprachen sowie (optional) "children"
    - src_lang - Sprache der vorhandenen zu klonenden Struktur;
                 ein Sprachkürzel und natürlich ein Schlüssel von <dic>

    Benannte Argumente:
    - switch_menu - sollen die neuen Ordner im Menü auftauchen?
                    (Vorgabe: True)
    - move_children - sollen die Kindobjekte in das jeweilige neue
                      sprachverknüpfte Verzeichnis verschoben werden?
    - move_limit - für Test/Entwicklung: max. Anzahl der insgesamt zu
                   verschiebenden Objekte, Vorgabe: None
    - move_limit_each - dto.; max. Anzahl pro behandeltem Containerverzeichnis.
    - rectify_moved - Subportal-Angaben korrigieren für schon zuvor verschobene
                      Kindobjekte
    - create_level - 1 (Vorgabe): erzeuge fehlende Sprachvarianten,
                     2: ... auch wenn der Referenzordner fehlt;
                     3: erzeuge auch etwa fehlende Referenzordner.
    - skip_unknown_languages - sollen Zielsprachen, die in der Plone-Instanz
                     nicht aktiviert sind, übergangen werden?
                     (Vorgabe: True)

    Hinweise:
    - Es ist möglich und sinnvoll, die Funktion mit denselben Eingabedaten erst
      ohne, dann mit move_children=True aufzurufen.
    - Ein globales move_limit=0 führt dazu, daß der Verschiebungs-Code ausgeführt,
      aber wegen Überschreitung des Limits nichts verschoben wird
    - Ein move_limit_each=0 bedeutet hingegen, daß keine Obergrenze je
      Verschiebungsvorgang existiert (wohl aber ggf. ein globales move_limit,
      das natürlich beachtet würde)
    - Jede Angabe von move_limit oder move_limit_each führt dazu, daß der
      Vorgabewert für move_children True ist (siehe _args._extract_move_args)

    Diese Funktion arbeitete rekursiv:

    1. zunächst kümmert sich die veröffentlichte Funktion clone_tree um die
       Auswertung der Optionen;
    2. dann wird rekursiv _clone_tree_inner aufgerufen. Jeder Aufruf verabeitet
       ein Teil-Dictionary mit folgenden Schlüsseln:

       'de', 'en' ... *(Sprachcodes)* - die Objektangaben je Sprache
       `None` - ein optionales Dict. für Optionen
       'children' - Eine Liste mit weiteren Verästelungen

       Die Optionen werden in einer Datenstruktur StackOfDicts verwaltet;
       so ist es möglich, an die Hauptfunktion `clone_tree` in Teilbäumen zu
       übersteuern.

    """
    # We'll consume this dictionary!
    # (We don't expect it to contain much data, anyway.)
    dic = deepcopy(dic)

    pop = kwargs.get
    setdefault = kwargs.setdefault
    # locally used options:
    if 'logger' in kwargs:
        logger = pop('logger')
    else:
        logger = kwargs.setdefault(
                    'logger',
                    logging.getLogger('clone_tree:%08x'
                                      % random.randint(0, 16**8)))
    verbose = setdefault('verbose', 1)
    create_level = setdefault('create_level', 1)
    debug = setdefault('debug', False)

    # Options for get_object; set, if given:
    setdefault('set_title', True)
    setdefault('set_language', True)
    set_canonical = setdefault('set_canonical', None)
    src_lang = setdefault_source_language(kwargs)
    if not src_lang:
        raise ValueError('Currently a source_language is needed!')
    if src_lang not in dic:
        raise ValueError('input dict. lacks data'
                ' for the source language %(src_lang)r'
                % locals())

    setdefault('get_uid', True)
    setdefault('get_layout', True)

    if 'portal' in kwargs:
        portal = kwargs['portal']
    else:
        portal = getToolByName(context, 'portal_url').getPortalObject()
        kwargs['portal'] = portal
    if 'allowed_languages' in kwargs:
        allowed_languages = kwargs['allowed_languages']
    else:
        portal_languages = getToolByName(context, 'portal_languages')
        allowed_languages = portal_languages.getSupportedLanguages()
        kwargs['allowed_languages'] = allowed_languages
    logger.info('allowed languages are %(allowed_languages)r', locals())
    if src_lang not in allowed_languages:
        logger.warn('Source language %(src_lang)r is not listed as an allowed one!', locals())
    setdefault('skip_unknown_languages', not allowed_languages)

    normalize_menu_switch(kwargs)

    opt = StackOfDicts(kwargs, checked=0)
    info_collector = {
            'finally_reindex': [],
            'counter': Counter(),
            }
    try:
        return _clone_tree_inner(context, dic, opt, info_collector, {}, 0)
    finally:
        transaction.commit()
        finally_reindex = info_collector['finally_reindex']
        counter = info_collector['counter']
        pp(counter=counter)
        if finally_reindex:
            total = len(finally_reindex)
            i = 0
            for o in finally_reindex:
                i += 1
                logger.info('Reindexing %(i)d/%(total)d: %(o)r ...', locals())
                o.reindexObject()
                transaction.commit()
        errors = counter.pop('errors', 0)
        for key, val in counter.items():
            logger.info('  %(key)s: %(val)d', locals())
        if errors:
            logger.error('%(errors)d errors total', counter)
    # -------------------------------------------------- ] ... clone_tree ]


def _clone_tree_inner(context,  # --------------- [ _clone_tree_inner ... [
                      dic,  # the consumed data definition
                      opt,  # a StackOfDicts
                      info_collector,  # globally cumulated information
                      parents_o,  # `siblings_o` dict from above
                      recursion_level):
    """
    The working horse for the clone_tree function (recursive)
    """
    logger = opt['logger']

    # -------------------------- [ options dictionary processing ... [
    local_options = dic.pop(None, {})
    if local_options.get('debug'):
        logger.info('_clone_tree_inner: local debug option found; will fire again below', locals())
        set_trace()
    elif dic.get('debug'):
        logger.info('_clone_tree_inner: inherited debug option found; may fire again below', locals())
        set_trace()

    opt.push(local_options)  # local options overrides from dict

    # currently we still demand a source_language
    src_lang = opt['source_language']
    src_dict = dic.pop(src_lang)
    children = dic.pop('children', [])

    siblings_o = {}   # used during recursion
    siblings_opt = {  # options
        src_lang: src_dict.pop(None, {}),
        }
    # -------------------------- ] ... options dictionary processing ]

    counter = info_collector['counter']
    finally_reindex = info_collector['finally_reindex']

    # ----------------------------- [ _clone_tree_inner: options ... [
    create_level = opt['create_level']
    logger.info('Create_level is %(create_level)r', locals())
    create_all = create_level >= 3
    if create_all:
        logger.info('Will create all specified folders,'
                ' including missing reference folders')
    create_orphans = create_level >= 2
    if create_orphans:
        logger.info('Will create all language variants'
                ' even for missing reference folders')
    create_normal = create_level >= 1
    if create_normal:
        logger.info('Will create all specified language variants')
    else:
        logger.info("Won't create any folders")
    portal = opt['portal']
    catalog = getToolByName(portal, 'portal_catalog')
    # ----------------------------- ] ... _clone_tree_inner: options ]
    idxs = [
        'getExcludeFromNav',
        'Language',
        # UNITRACC-spezifisch; visaplan.plone.subportals:
        'get_sub_portal',
        ]

    new_folder = make_subfolder_creator(logger=opt['logger'],
                                        parent=portal,
                                        idxs=idxs)
    get_object = make_object_getter(portal,
                                    logger=opt['logger'],
                                    set_title=opt['set_title'],
                                    set_language=opt['set_language'],
                                    set_canonical=opt['set_canonical'],
                                    get_uid=True,
                                    get_layout=opt['get_layout'],
                                    set_subportal=opt.get('set_subportal'),
                                    subportal=opt.get('subportal'),
                                    return_tuple=True,
                                    verbose=2)

    errors = 0

    if opt.get('debug'):
        logger.info('_clone_tree_inner: initialization done; debug option found in %(opt)r', locals())
        # pp(opt=dict(opt))
        set_trace()

    move_children, move_limit, move_limit_each = _extract_move_args(opt, do_pop=0)
    if move_children:
        reindex = False  # Container erst am Schluß reindizieren
    else:
        reindex = None

    try:
        pp(src_dict=src_dict, recursion_level=recursion_level, parents_o=parents_o)
        if src_lang in parents_o:
            src_dict['parent'] = parents_o[src_lang]
        src_o, info = get_object(reindex=reindex,
                                 **src_dict)
        if src_o is None:
            specs = info['specs']
            raise ValueError('source path %(specs)s (%(src_lang)r) NOT FOUND!'
                             % locals())
        else:
            siblings_o[src_lang] = src_o
        src_dict.update(info['updates'])
        assert src_dict['uid']

        # q&d; we might want a smarter comparison method which tells
        # whether 2 dicts specify the same object (e.g. by uid, if present):
        src_path = src_dict.get('path', None)
        logger.info('source path is %(src_path)r (%(src_lang)r, %(src_o)r)',
                    locals())
        # transaction.begin()  # ist das schlau bzw. nötig?!
        if info['changes'] and not info['reindexed']:
            finally_reindex.append(src_o)

        # ... alle verbleibenden Schlüssel sind nun Sprachkürzel!

        # Wir wissen noch nicht, ob alle Kinder im selben Elternobjekt
        # verbleiben:
        same_parent = None
        canonical = None

        # --------------- [ Schleife über die *anderen* Sprachen ... [
        for la in dic.keys():
            if la not in opt['allowed_languages']:
                if opt['skip_unknown_languages']:
                    logger.error('SKIP: Clone language %(la)r is '
                                 'not listed as an allowed one!', locals())
                    continue
                else:
                    logger.warn('Clone language %(la)r is '
                                'not listed as an allowed one!', locals())
            dest_dict = dic[la]
            siblings_opt[la] = dest_dict.pop(None, {})
            if la in parents_o:
                dest_dict['parent'] = parents_o[la]
            if ('layout' in src_dict
                    and src_dict['layout']
                    and 'layout' not in dest_dict
                    and dest_dict.get('set_layout') is not False):
                logger.debug('Taking layout=%(layout)r from source folder', src_dict)
                dest_dict.update({
                    'layout': src_dict['layout'],
                    'set_layout': True,
                    })

            # -- [ gemeinsamer Container für alle Sprachen? ... [
            dest_o, info = get_object(**dest_dict)
            if dest_o is None:
                # das Elternobjekt für diese Sprache gibt es noch nicht,
                # also ist es ein anderes!
                if same_parent:
                    logger.error('We have same_parent=%(same_parent)r, '
                            'but the spec. for %(la)r (%(dest_dict)r) '
                            "doesn't exist yet!",
                            locals())
                    errors += 1
                    continue
                elif same_parent is None:
                    same_parent = False
                if create_normal:
                    dest_o = new_folder(**dest_dict)
                elif debug:
                    pp(dest_dict=dest_dict)
                    retry = 1; set_trace()
                    if retry:
                        dest_o = new_folder(**dest_dict)
            else:
                dest_dict.update(info['updates'])
                if same_parent is None:
                    same_parent = dest_dict['uid'] == src_dict['uid']
                elif same_parent:
                    if dest_dict['uid'] != src_dict['uid']:
                        dest_uid = dest_dict['uid']
                        src_uid = src_dict['uid']
                        logger.error('We have same_parent=%(same_parent)r, but '
                                'the %(la)r container object %(dest_uid)r '
                                'mismatches '
                                'the %(src_lang)r container object %(src_uid)r!',
                                locals())
                        errors += 1
                        continue
                else:
                    if dest_dict['uid'] == src_dict['uid']:
                        dest_uid = dest_dict['uid']
                        logger.error('We have same_parent=%(same_parent)r, but '
                                'the both %(src_lang)r and %(la)r '
                                'use the same container object'
                                ' %(dest_uid)r!',
                                locals())
                        errors += 1
                        continue
            siblings_o[la] = dest_o
            assert same_parent is not None
            # -- ] ... gemeinsamer Container für alle Sprachen? ]
            if same_parent:
                given_src_lang = src_dict.get('language')
                if given_src_lang:
                    logger.error('We have same_parent=%(same_parent)r, but '
                            'the source parent has language=%(given_src_lang)r '
                            'specified! (%(src_dict)s)', locals())
                    raise ValueError('Language specs')
            elif canonical is None:
                # Erster Schleifendurchlauf (erste "Zweitsprache"):
                canonical = src_o.getCanonical()  # Sprachverknüpfung
                logger.info('%(src_o)r.getCanonical() --> %(canonical)r', locals())
                src_dict.update({
                    'canonical': canonical,
                    'language': src_lang,
                    })
                info = get_object(reindex=reindex, **src_dict)[1]
                if info['changes']:
                    logger.info('Source container was changed (%(src_o)r)', locals())
            if same_parent:
                dest_dict.update({
                    'language': '',
                    })
            else:
                if opt['set_language']:
                    dest_dict.update({
                        'language': la,
                        })
                if opt['set_canonical']:
                    dest_dict.update({
                        'canonical': canonical,
                        })
            o, info = get_object(**dest_dict)
            if info['changes']:
                logger.info('Dest. container for %(la)r was changed (%(dest_o)r)', locals())
        # --------------- ] ... Schleife über die *anderen* Sprachen ]

        # -------------------- [ unitracc; visaplan.plone.search ... [
        if HAS_VPSEARCH and opt.get('united_search'):
            handle_united_search(siblings_o, opt, src_lang)
        # -------------------- ] ... unitracc; visaplan.plone.search ]

        for la, dest_dict in dic.items():
            opt.push(siblings_opt[la])

            try:
                # --- [ unitracc-spezifisch: Subportal korrigieren ... [
                rectify_moved = opt.get('rectify_moved', False)
                if rectify_moved:
                    doit = True
                    subportal = opt.get('subportal')
                    if not subportal:
                        logger.warn('rectify_moved=%(rectify_moved)r, but no subportal!', dict(opt))
                        doit = False

                    child_set_subportal = opt.get('child_set_subportal', False)
                    if not child_set_subportal:
                        logger.warn('rectify_moved=%(rectify_moved)r,'
                                    ' but not child_set_subportal!', dict(opt))
                        doit = False

                    if doit:
                        force_reindex = opt.get('force_reindex')
                        reindex = make_reindexer(logger=logger, catalog=catalog,
                                                 idxs=idxs,
                                                 # getSubPortals will change:
                                                 update_metadata=True)
                        tup = o.getPhysicalPath()
                        root_path = '/'.join(tup)
                        query = dict(path=root_path, Language=la)
                        apply_move_order_options(query, opt, do_pop=0)
                        batch_kw = {'batch_size': 100,
                                    'thingies': 'checking subportal for objects',
                                    }
                        # ---------- [ TODO: vereinheitlichen ... [
                        # (im einen Fall kommt der Wert aus der Funktion
                        # (child_set_subportal), im anderen muß er selbst
                        # gebaut werden. Besser eine von v.p.subportals
                        # erzeugte Funktion verwenden, die sich um alles
                        # kümmert und einen Wahrheitswert (geändert?)
                        # zurückgibt.)
                        if callable(child_set_subportal):
                          for batch, txt in batch_tuples(catalog(**query),
                                                         **batch_kw):
                            changes_here = 0
                            logger.info(txt + ' ...')
                            for brain in batch:
                                if brain.getPath() == root_path:  # not a child!
                                    continue
                                ch, val = child_set_subportal(brain=brain)
                                if ch or force_reindex:
                                    child_o = brain.getObject()
                                if ch:
                                    child_o.setSubPortals(val)
                                    counter['subportal_fixed'] += 1
                                    changes_here += 1
                                else:
                                    counter['subportal_checked'] += 1
                                if ch or force_reindex:
                                    if reindex(o=child_o):
                                        counter['children_reindexed'] += 1
                            if changes_here:
                                logger.info('%(changes_here)d changes; '
                                            'committing transaction ...',
                                            locals())
                                transaction.commit()
                        else:
                          for batch, txt in batch_tuples(catalog(**query),
                                                         **batch_kw):
                            changes_here = 0
                            logger.info(txt + ' ...')
                            for brain in batch:
                                if brain.getPath() == root_path:  # not a child!
                                    continue
                                val = brain.getSubPortals
                                ch = subportal not in val
                                if ch or force_reindex:
                                    child_o = brain.getObject()
                                if ch:
                                    child_o.setSubPortals(val + (subportal,))
                                    counter['subportal_fixed'] += 1
                                    changes_here += 1
                                else:
                                    counter['subportal_checked'] += 1
                                if ch or force_reindex:
                                    if reindex(o=child_o):
                                        counter['children_reindexed'] += 1
                            if changes_here:
                                logger.info('%(changes_here)d changes; '
                                            'committing transaction ...',
                                            locals())
                                transaction.commit()
                        # ---------- ] ... TODO: vereinheitlichen ]
                # --- ] ... unitracc-spezifisch: Subportal korrigieren ]

                if move_children:
                    src_child_o = siblings_o.get(src_lang)
                    if not src_child_o:
                        logger.error('Moving impossible because of missing '
                                     'source folder!')
                        errors += 1
                        move_children = False

                if move_children:
                    dest_child_o = siblings_o.get(la)
                    if dest_child_o is None:
                        logger.error('Moving impossible '
                                     'because of missing destination folder! '
                                     '(%(specs)s)',
                                     info)
                        errors += 1
                        continue

                    child_kwargs = {
                        'move_limit': move_limit,
                        'move_limit_each': move_limit_each,
                        'depth': 1,
                        }
                    subportal = opt.get('subportal')
                    set_subportal = opt.get('child_set_subportal')
                    if subportal and set_subportal:
                        child_kwargs.update({
                            'subportal': subportal,
                            'set_subportal': set_subportal,
                            })
                    move_types = opt.get('move_types') or []
                    for portal_type in move_types:
                        _move_objects(src_child_o, dest_child_o,
                                      portal_type, la,
                                      logger, counter,
                                      **child_kwargs)

                    take_types = opt.get('take_types') or []
                    for portal_type in take_types:
                        _move_objects(src_o, dest_child_o,
                                      portal_type, la,
                                      logger, counter,
                                      **child_kwargs)
                    transaction.commit()
            finally:
                opt.pop()

        # Wir haben jetzt src_o, dest_o und same_parent;
        # nun können wir in dest_o die neuen sprachverknüpften Kindelemente
        # suchen bzw. neu erstellen

        # nun die Unterordner:
        for child_dict in children:
            pp(('siblings_o:', siblings_o), ('child_dict:', child_dict))
            _clone_tree_inner(context, child_dict, opt, info_collector,
                              siblings_o,
                              recursion_level+1)

    finally:
        if errors:
            logger.error('%(errors)d errors here', locals())
            counter['errors'] += errors

    # ------------------------------------------- ] ... _clone_tree_inner ]


def _move_objects(from_o, to_o,  # ------------------ [ _move_objects ... [
                  portal_type, lang, logger, cnt,
                  **kwargs):
    """
    Helper for clone_tree(move_children)
    """
    kwargs = dict(kwargs)
    pop = kwargs.pop
    depth = pop('depth', 1)
    assert depth == 1, (
        'depth=%(depth)r: other depths than 1 are not yet implemented!'
        ) % locals()
    query = {
        'portal_type': portal_type,
        'Language': lang,
        }
    query_path = '/'.join(from_o.getPhysicalPath())
    if depth is None:
        query['path'] = query_path
        raise NotImplemented
    else:
        query['path'] = {
                'query': query_path,
                'depth': depth,
                }
    apply_move_order_options(query, kwargs)

    catalog = getToolByName(from_o, 'portal_catalog')
    brains = catalog(query)
    count_here = len(brains)
    if not count_here:
        logger.info('No %(portal_type)r objects of language %(lang)r in %(query_path)r', locals())
        return 0
    logger.info('Found %(count_here)d %(portal_type)r objects of language %(lang)r in %(query_path)r', locals())
    move_limit = pop('move_limit', None)
    move_limit_each = pop('move_limit_each', None)
    if move_limit is not None and cnt['moved_total'] >= move_limit:
        logger.info('Total move limit exceeded (%(move_limit)r)', locals())
        return 0

    try:
        if HAS_SUBPORTALS:
            consider_sp = might_set_subportal(kwargs)  # unitracc-specific
            one_by_one = portal_type == 'Folder' or consider_sp
        else:
            consider_sp = False
            one_by_one = portal_type == 'Folder'
        if one_by_one:
            i = 0
            for brain in brains:
                i += 1
                if move_limit_each and i > move_limit_each:
                    logger.info('Local move limit exceeded (%(move_limit_each)r)', locals())
                    return move_limit_each

                to_move = brain.getId
                if consider_sp:  # unitracc-specific
                    o = brain.getObject()
                    handle_subportal(o, kwargs, created=False, do_pop=False)
                    # we don't really care whether it was changed; it will be
                    # reindexed after moving anyway!

                logger.info('(%(i)d/%(count_here)d) move %(to_move)r ...', locals())
                cp = from_o.manage_cutObjects(ids=(to_move,))
                to_o.manage_pasteObjects(cp)
                transaction.commit()
                cnt['moved_total'] += 1
                if move_limit and cnt['moved_total'] >= move_limit:
                    logger.info('Total move limit exceeded (%(move_limit)r)', locals())
                    return i
            return i

        local_limits = []
        if move_limit_each is not None:
            local_limits.append(move_limit_each)
        if move_limit is not None:
            local_limits.append(move_limit - cnt['moved_total'])
        unlimited = not local_limits
        if not unlimited:
            local_limit = min(local_limits)
            if local_limit >= count_here:
                unlimited = True

        if unlimited:
            batch_size = pop('batch_size', 10)
            all_ids = [brain.getId for brain in brains]
            # TODO: use visaplan.tools.batches.batch_tuples 
            if batch_size and batch_size < count_here:
                logger.info('Moving %(count_here)d %(portal_type)r objects'
                ' of language %(lang)r'
                ' in batches of %(batch_size)d'
                ' to %(to_o)r ...', locals())
                total_found = len(all_ids)
                full_batches, in_last = divmod(total_found, batch_size)
                total_batches = full_batches
                if in_last:
                    total_batches += 1
                batch_nr = 0
                while all_ids:
                    batch = all_ids[:batch_size]
                    del     all_ids[:batch_size]
                    first_nr = batch_nr * batch_size + 1
                    last_nr = min(total_found, (batch_nr+1) * batch_size)
                    this_batch_size = last_nr + 1 - first_nr
                    batch_nr += 1
                    logger.info('Objects %(first_nr)d to %(last_nr)d'
                                ' (batch %(batch_nr)d / %(total_batches)d) ...',
                                locals())
                    cp = from_o.manage_cutObjects(ids=batch)
                    res = to_o.manage_pasteObjects(cp)
                    transaction.commit()
            else:
                logger.info('Moving %(count_here)d %(portal_type)r objects of language %(lang)r to %(to_o)r ...', locals())
                cp = from_o.manage_cutObjects(ids=all_ids)
                res = to_o.manage_pasteObjects(cp)
                transaction.commit()
                pp(res=res)
            logger.info('Done: Pasted %(count_here)d objects in %(to_o)r', locals())
            cnt['moved_total'] += count_here
            return count_here

        ids = []
        i = 0
        for brain in brains:
            ids.append(brain.getId)
            i += 1
            if i >= local_limit:
                break

        logger.info('Moving %(local_limit)d / %(count_here)d %(portal_type)r objects of language %(lang)r to %(to_o)r ...', locals())
        cp = from_o.manage_cutObjects(ids=ids)
        to_o.manage_pasteObjects(cp)
        logger.info('Done: Pasted %(local_limit)d objects in %(to_o)r', locals())
        cnt['moved_total'] += local_limit
        return local_limit
    finally:
        transaction.commit()
    # ----------------------------------------------- ] ... _move_objects ]

def _skip_language(la, dic):
    """
    Helper for _clone_tree_inner: Skip the given language?
    """
    logger = dic['logger']
    allowed_languages = dic.get('allowed_languages')
    if not allowed_languages:
        logger.warn('no allowed languages information')
        return False
    if la in allowed_languages:
        return False

