# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Python compatibility:
from __future__ import absolute_import

# Standard library:
from posixpath import normpath

# Zope:
from Products.CMFCore.utils import getToolByName

# Plone:
from plone.uuid.interfaces import IUUID

# Local imports:
from visaplan.plone.tools._have import HAS_SUBPORTALS
from visaplan.plone.tools.setup._args import (
    _extract_move_args,
    extract_layout_switch,
    extract_menu_switch,
    )
from visaplan.plone.tools.setup._misc import _traversable_path
from visaplan.plone.tools.setup._o_tools import (
    handle_language,
    handle_layout,
    handle_menu,
    handle_title,
    make_notes_logger,
    )

if HAS_SUBPORTALS:
    from visaplan.plone.tools.setup._o_tools import handle_subportal

# Local imports:
from visaplan.plone.tools.setup._reindex import make_reindexer

# Logging / Debugging:
import logging

# Exceptions:




__all__ = [
        'make_object_getter',
        ]


# see also _make_folder.py: make_subfolder_creator
def make_object_getter(context, **kwargs):
    """
    Return a function which finds an object ...

    - by 'id', if a 'parent' is given;
    - by 'uid' (if given);
    - by 'path' (relative to the portal object).

    Getting the object is the first part only; the function is used to make
    sure the object has certain properties as well!

    Further understood options are:
    - title - a title to be checked and/or set
    - language - a language to be checked and/or set
    - canonical - an object which was returned by some .getCanonical method
                  call. Usually requires a language value as well.
    - info - a (usually empty) dict; see `return_tuple` below.

    Options to the factory:
    - keys - the sequence of the keys 'id', 'uid' and 'path',
             specifying the order in which they are tried
    - verbose - log informations about problems
    - logger - a logger to use if verbose
    ... defaults for the function:
    - set_title - set the title (if given and not matching)
    - set_uid - set the UUID (if given and not matching)
    - set_language - set the language (if given and not matching)
    - set_canonical - link the canonical translation (if given)
    - reindex - True:  reindex in any case,
                False: ... under no circumstances,
                None:  ... if changes were made (default).
    - return_tuple - if True, return a 2-tuple (object, info);
                     by default, only the object (or None) is returned.

    Unless return_tuple=True is specified,
    the returned function will simply return the object or None;
    in this (standard) case, you can deliver the info dictionary yourself,
    which will be changed in-place, to get access to the
    detailed information, including an "updates" subdict.

    The "set_..." options mean, "set the object property", e.g. call
    setLanguage if a language key is given and mismatching;
    the "get_..." options do the opposite: they write the found value to the
    info dictionary, to be more precise: to the info['updates'] dictionary.
    Thus, to make use of the get_... results, an "info" dictionary must be
    provided.
    """
    pop = kwargs.pop
    keys = pop('keys', None) or ['path', 'id', 'uid']
    parent = pop('parent', None)
    portal = getToolByName(context, 'portal_url').getPortalObject()
    reference_catalog = getToolByName(context, 'reference_catalog')
    verbose = pop('verbose', 1)
    if 'logger' in kwargs:
        logger = pop('logger')
    elif verbose:
        logger = logging.getLogger('get_object')
    reindexer = kwargs.pop('reindexer', None)
    idxs = kwargs.pop('idxs', None)
    if reindexer is None and (set_menu is None or set_menu):
        reindexer = make_reindexer(logger=logger,
                                   context=parent,
                                   idxs=idxs)
    elif reindexer is not None and idxs is not None:
        logger.warn('Ignoring idxs value %(idxs)r', locals())
    reindex = kwargs.pop('reindex', reindexer is not None
                                    or None)
    if reindex and reindexer is None:
        reindexer = make_reindexer(logger=logger,
                                   context=parent)
    set_title =    pop('set_title', True)
    set_uid =      pop('set_uid', False)
    get_uid     =  pop('get_uid', None)
    set_language = pop('set_language', True)
    set_canonical = pop('set_canonical', None)
    if set_canonical is None:
        set_canonical = set_language
    set_subportal = pop('set_subportal', None)
    subportal     = pop('subportal', None)
    return_tuple = pop('return_tuple', False)

    def _err(msg, notes, logger=logger):
        notes.append(('ERROR', msg))
        if logger is not None:
            logger.error(msg)

    def _info(msg, notes, log=True, logger=logger):
        notes.append(('INFO', msg))
        if log and logger is not None:
            logger.info(msg)

    def get_object(
            id=None, uid=None, path=None,
            info=None,  # specify an empty dict to get information!
            parent=parent,
            reindex=reindex,
            reindexer=reindexer,
            set_title=set_title,
            set_uid=set_uid,
            get_uid=get_uid,
            set_language=set_language,
            set_canonical=set_canonical,
            set_subportal=set_subportal,
            subportal=subportal,
            return_tuple=return_tuple,
            **kwargs):
        """
        This function is designed to be called with keyword arguments only.

        In a Python-3-only release of the package, this will be enforced!
        """
        if info is None:
            info = {}
        info.update({
            'found':     False,
            'reindexed': False,
            'changes':   0,
            'notes':     [],
            'specs':     None,  # set to a string below
            'updates':   {},
            })
        notes = info['notes']
        # for notes from _o_tools.py:
        lognotes = make_notes_logger(logger, info['notes'])

        updates = info['updates']
        tried_keys = set()
        o = None
        found_by = None
        changes = 0
        specs = []
        for key in keys:
            if key in tried_keys:
                continue
            tried_keys.add(key)
            if key == 'id':
                if id is not None:
                    specs.append('id=%(id)r' % locals())
                    if parent is not None:
                        o = getattr(parent, id, None)
                        if o is None:
                            _err('%(parent)r.%(id)r not found!' % locals(),
                                 notes)
            elif key == 'uid':
                if uid is not None:
                    specs.append('uid=%(uid)r' % locals())
                    o = reference_catalog.lookupObject(uid)
                    if o is None:
                        _err('UID %(uid)r not found!' % locals(),
                             notes)
            elif key == 'path':
                if path is not None:
                    specs.append('path=%(path)r' % locals())
                    if normpath(path) in ('.', '/'):
                        o = portal
                        _info('path=%(path)r -> using %(portal)r!' % locals(),
                              notes)
                    else:
                        try:
                            # restrictedTraverse dislikes leading slashes, at least:
                            o = portal.restrictedTraverse(_traversable_path(path))
                        except KeyError:
                            o = None
                    if o is None:
                        _err('%(portal)r[%(path)r] not found!' % locals(),
                             notes)
            else:
                _err('Unknown key: %(key)r' % locals(), notes)

            if found_by is None and o is not None:
                found_by = key
                break

        info['specs'] = ', '.join(specs) or 'no non-empty specifications!'
        if o is None:
            return ((o, info) if return_tuple
                    else o)

        info['found'] = True
        info['found_by'] = found_by

        if found_by == 'uid':
            if get_uid >= 2:
                updates['uid'] = uid
        else:
            if get_uid is None:
                get_uid = True
            if get_uid or uid is not None:
                found_uid = IUUID(o, None)
                if uid is not None:
                    if found_uid != uid:
                        if set_uid:
                            o._setUID(uid)
                            _info('%(o)r: old UID %(found_uid)r --> new UID %(uid)r'
                                  % locals(),
                                  notes)
                            changes += 1
                            if get_uid:
                                found_uid = uid
                        else:
                            _info('%(o)r: UID %(found_uid)r mismatches %(uid)r'
                                  % locals(),
                                  notes)
                    else:
                        _info('%(o)r: checked UID (%(found_uid)r)' % locals(),
                              notes,
                              verbose > 1)
            if get_uid:
                updates['uid'] = found_uid

        # ---------- [set_]title:
        kwargs.update(set_title=set_title)
        ch, notes = handle_title(o, kwargs, created=False)
        changes += ch
        for tup in notes:
            lognotes(tup)

        # ---------- [set_]language, [set_]canonical:
        kwargs.update(set_language=set_language, set_canonical=set_canonical)
        ch, notes = handle_language(o, kwargs, created=False)
        changes += ch
        for tup in notes:
            lognotes(tup)

        # ---------- [{set,get}_]layout:
        ch, notes, upd = handle_layout(o, kwargs, created=False)
        changes += ch
        for tup in notes:
            lognotes(tup)
        updates.update(upd)  # might contain a new 'layout' key

        # ---------- [switch_]menu:
        ch, notes = handle_menu(o, kwargs, created=False)
        changes += ch
        for tup in notes:
            lognotes(tup)

        if HAS_SUBPORTALS:
            # ---------- [set_]subportal:
            kwargs.update(subportal=subportal, set_subportal=set_subportal)
            ch, notes = handle_subportal(o, kwargs, created=False)
            changes += ch
            for tup in notes:
                lognotes(tup)

        info['changes'] = changes
        if reindex is None:
            if not changes:
                _info('%(o)r not changed and not reindexed' % locals(),
                      notes)
                return ((o, info) if return_tuple
                        else o)
            reindex = True
        if not reindex:
            if changes:
                _info('%(o)r has %(changes)d changes but reindexing suppressed'
                      % locals(),
                      notes)
            return ((o, info) if return_tuple
                    else o)
        if reindexer is None:
            o.reindexObject()
        else:
            reindexer(o)
        info['reindexed'] = True
        return ((o, info) if return_tuple
                else o)

    return get_object
