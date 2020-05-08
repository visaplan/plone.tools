# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Standardmodule
from string import capitalize
from collections import defaultdict
from functools import wraps
from time import time
from copy import deepcopy
from collections import Counter
from posixpath import normpath

# Exceptions:
from ZODB.POSException import POSKeyError

# Plone, sonstiges:
from plone.uuid.interfaces import IUUID
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

# local imports from sister modules:
from ._reindex import (
        make_reindexer,
        )
from ._args import (
        extract_menu_switch,
        extract_layout_switch,
        _extract_move_args,
        )
from ._get_object import (
        make_object_getter,
        )
from ._make_folder import (
        make_subfolder_creator,
        )

__all__ = [
        'clone_tree',  # sprachverknüpfter Verzeichnisbaum
        ]


def clone_tree(context, dic, src_lang, **kwargs):
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
    - create_level - 1 (Vorgabe): erzeuge fehlende Sprachvarianten,
                     2: ... auch wenn der Referenzordner fehlt;
                     3: erzeuge auch etwa fehlende Referenzordner.

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
    """
    pop = kwargs.pop
    if 'logger' in kwargs:
        logger = pop('logger')
    else:
        logger = logging.getLogger('clone_tree')
    if src_lang not in dic:
        raise ValueError('input dict. lacks data'
                ' for the source language %(src_lang)r'
                % locals())

    if 'create_level' in kwargs:
        create_level = pop('create_level')
    else:
        create_level = 1
        logger.info('Default create_level is %(create_level)r', locals())
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
    debug = pop('debug', False)

    # We'll consume this dictionary!
    # (We don't expect it to contain much data, anyway.)
    dic = deepcopy(dic)

    src_dict = dic.pop(src_lang)
    portal = getToolByName(context, 'portal_url').getPortalObject()
    portal_languages = getToolByName(context, 'portal_languages')
    allowed_languages = portal_languages.getSupportedLanguages()
    logger.info('allowed languages are %(allowed_languages)r', locals())
    if src_lang not in allowed_languages:
        logger.warn('Source language %(src_lang)r is not listed as an allowed one!', locals())
    reference_catalog = getToolByName(context, 'reference_catalog')
    switch_menu = extract_menu_switch(kwargs, True)
    dic_nr = 0
    copies = 0
    errors = 0
    errors_total = 0
    counter = Counter()
    new_folder = make_subfolder_creator(logger=logger,
                                        parent=portal,
                                        switch_menu=switch_menu)
    get_object = make_object_getter(portal,
                                    logger=logger,
                                    set_title=True,
                                    set_language=True,
                                    get_uid=True,
                                    get_layout=True,
                                    return_tuple=True,
                                    verbose=2)
    move_children, move_limit, move_limit_each = _extract_move_args(kwargs, 1)
    if move_children:
        reindex = False  # Container erst am Schluß reindizieren
    else:
        reindex = None

    finally_reindex = []
    try:
        src_o, info = get_object(reindex=reindex,
                                 **src_dict)
        if src_o is None:
            specs = info['specs']
            raise ValueError('source path %(specs)s (%(src_lang)r) NOT FOUND!'
                             % locals())
        src_dict.update(info['updates'])

        # q&d; we might want a smarter comparison method which tells
        # whether 2 dicts specify the same object (e.g. by uid, if present):
        src_path = src_dict.get('path', None)
        logger.info('source path is %(src_path)r (%(src_lang)r, %(src_o)r)',
                    locals())
        transaction.begin()
        assert src_dict['uid']
        if info['changes'] and not info['reindexed']:
            finally_reindex.append(src_o)

        children = dic.pop('children')
        # ... alle verbleibenden Schlüssel sind nun Sprachkürzel!

        # Wir wissen noch nicht, ob alle Kinder im selben Elternobjekt
        # verbleiben:
        same_parent = None
        parents_dict = {src_lang: src_o}
        canonical = None

        # --------------- [ Schleife über die *anderen* Sprachen ... [
        for dest_lang in dic.keys():
            if dest_lang not in allowed_languages:
                logger.warn('Clone language %(dest_lang)r is not listed as an allowed one!', locals())
            dest_dict = dic.pop(dest_lang)
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
                            'but the spec. for %(dest_lang)r (%(dest_dict)r) '
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
                                'the %(dest_lang)r container object %(dest_uid)r '
                                'mismatches '
                                'the %(src_lang)r container object %(src_uid)r!',
                                locals())
                        errors += 1
                        continue
                else:
                    if dest_dict['uid'] == src_dict['uid']:
                        dest_uid = dest_dict['uid']
                        logger.error('We have same_parent=%(same_parent)r, but '
                                'the both %(src_lang)r and %(dest_lang)r '
                                'use the same container object'
                                ' %(dest_uid)r!',
                                locals())
                        errors += 1
                        continue
            parents_dict[dest_lang] = dest_o
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
                dest_dict.update({
                    'canonical': canonical,
                    'language': dest_lang,
                    })
            info = get_object(**dest_dict)[1]
            if info['changes']:
                logger.info('Dest. container for %(dest_lang)r was changed (%(dest_o)r)', locals())
        # --------------- ] ... Schleife über die *anderen* Sprachen ]

        # Wir haben jetzt src_o, dest_o und same_parent;
        # nun können wir in dest_o die neuen sprachverknüpften Kindelemente
        # suchen bzw. neu erstellen

        # nun die Unterordner:
        for child_dict in children:
            pp(('dest_lang:', dest_lang), ('child_dict:', child_dict))
            src_child_dict = child_dict.pop(src_lang)
            src_child_dict.update({
                'language': src_lang,
                })

            # local options (for the current language-connected set of children):
            child_options = {
                    'menu': True,
                    'move_types': [],
                    'take_types': [],
                    }
            child_options.update(child_dict.pop(None, {}))

            src_child_o, info = get_object(parent=src_o, **src_child_dict)
            if src_child_o is None:
                msg = 'Reference folder (specs=%(specs)r) missing!' % info
                if create_all:
                    logger.info(msg)
                    src_child_o = new_folder(**src_child_dict)
                else:
                    logger.error(msg)

            dest_child_update = {
                    'parent': parents_dict[dest_lang],
                    'menu': child_options['menu'],
                    }
            if src_child_o is not None:
                get_object(**src_child_dict)

                src_canonical = src_child_o.getCanonical()
                if src_child_o is src_canonical:
                    logger.info('OK: %(src_child_o)r is the canonical object', locals())
                else:
                    logger.warn('%(src_child_o)r is not canonical! (%(src_canonical)r)', locals())

                # common values for connected children:
                dest_child_update.update({
                        'layout': src_child_o.getLayout(),
                        'canonical': src_canonical,
                        })

            for dest_lang, dest_child_dict in child_dict.items():
                if dest_lang not in parents_dict:
                    if same_parent:
                        parents_dict[dest_lang] = src_o
                        logger.info('Using %(src_o)r for %(dest_lang)r children', locals())
                    else:
                        logger.error('No container for %(dest_lang)r children!', locals())
                        errors += 1
                        continue
                dest_child_dict.update(dest_child_update)
                dest_child_dict['language'] = dest_lang
                dest_child_o, info = get_object(**dest_child_dict)
                if dest_child_o is None:
                    if create_normal:
                        logger.info('Create target folder (%(specs)r) ...', info)
                        dest_child_o = new_folder(**dest_child_dict)
                        logger.info('Created: %(dest_child_o)r', locals())
                        get_object(**dest_child_dict)
                    else:
                        logger.warn('Target folder (specs=%(specs)r) not yet created', info)
                                         
                # move_limit, move_limit_each = _extract_move_args(kwargs, 1)
                if move_children:
                    if dest_child_o is None:
                        logger.error('Moving impossible '
                                     'because of missing destination folder! '
                                     '(%(specs)s)',
                                     info)
                        continue
                    if src_child_o is None:
                        logger.error('Moving to %(dest_child_o)r impossible '
                                     'because of missing source folder!',
                                     locals())
                        continue
                    for portal_type in child_options['move_types']:
                        _move_objects(src_child_o, dest_child_o,
                                      portal_type, dest_lang,
                                      logger, counter,
                                      move_limit=move_limit,
                                      move_limit_each=move_limit_each,
                                      depth=1)

                    for portal_type in child_options['take_types']:
                        _move_objects(src_o, dest_child_o,
                                      portal_type, dest_lang,
                                      logger, counter,
                                      move_limit=move_limit,
                                      move_limit_each=move_limit_each,
                                      depth=1)

    finally:
        transaction.commit()
        if finally_reindex:
            total = len(finally_reindex)
            i = 0
            for o in finally_reindex:
                i += 1
                logger.info('Reindexing %(i)d/%(total)d: %(o)r ...', locals())
                o.reindexObject()
                transaction.commit()
        if errors:
            logger.error('%(errors)d errors here', locals())
            errors_total += errors
            errors = 0


def _move_objects(from_o, to_o, portal_type, lang, logger, cnt, **kwargs):
    """
    Helper for clone_tree(move_children)
    """
    kwargs = dict(kwargs)
    pop = kwargs.pop
    depth = pop('depth', 1)
    query = {
        'portal_type': portal_type,
        'Language': lang,
        }
    query_path = from_o.getPath()
    if depth is None:
        query['path'] = query_path
        raise NotImplemented
    else:
        query['path'] = {
                'query': query_path,
                'depth': depth,
                }

    catalog = getToolByName(from_o, 'portal_catalog')
    brains = portal_catalog(query)
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
        one_by_one = portal_type == 'Folder'
        if one_by_one:
            i = 0
            for brain in brains:
                i += 1
                if move_limit_each and i >= move_limit_each:
                    logger.info('Local move limit exceeded (%(move_limit_each)r)', locals())
                    return move_limit_each

                to_move = brain.getId
                logger.info('(%(i)d/%(count_here)d) move %(to_move)r ...', locals())
                cp = from_o.manage_cutObjects(ids=(to_move,))
                to_o.manage_pasteObjects(cp)
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
            logger.info('Moving %(count_here)d %(portal_type)r objects of language %(lang)r to %(to_o)r ...', locals())
            cp = from_o.manage_cutObjects(ids=[brain.getId for brain in brains])
            to_o.manage_pasteObjects(cp)
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
