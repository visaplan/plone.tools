# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Python compatibility:
from __future__ import absolute_import

# Standard library:
from posixpath import normpath
from string import capitalize

# Zope:
from Products.CMFCore.utils import getToolByName

# Local imports:
from visaplan.plone.tools.setup._args import (
    _extract_move_args,
    extract_layout_switch,
    extract_menu_switch,
    )
from visaplan.plone.tools.setup._misc import _traversable_path, make_title
from visaplan.plone.tools.setup._o_tools import (
    handle_language,
    handle_layout,
    handle_menu,
    handle_title,
    make_notes_logger,
    )
from visaplan.plone.tools.setup._reindex import make_reindexer

# Logging / Debugging:
import logging

__all__ = [
        'make_subfolder_creator',
        ]


# see also _get_object.py: make_object_getter
def make_subfolder_creator(**kwargs):
    """
    Erzeuge eine Funktion, die einen Ordner erzeugt und zurückgibt.
    Optionen, alle benannt zu übergeben:

    logger - der zu verwendende Logger
    title_factory - Funktion, um einen ggf. fehlenden Title zu erzeugen
    reindexer - wie von --> make_reindexer erzeugt

    Vorgabewerte für die zu erzeugende Funktion:

    set_menu - Soll die Aktivierung von Menüeinträgen umgeschaltet werden?
               Siehe ._args.extract_menu_switch.
    parent - das schon existierende ordnerartige Elternobjekt
    view_id - die ID der aufzuschaltenden Ansicht

    Argumene für einen zu erzeugenden Reindexer:

    idxs - eine Liste der zu aktualisierenden Indexe;
           make_reindexer wird per Vorgabe ['getId'] verwenden

    """
    parent = kwargs.pop('parent', None)
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('new folder')
    title_factory = kwargs.pop('title_factory', None)
    if title_factory is None:
        title_factory = make_title
    view_id, set_layout, get_layout = extract_layout_switch(kwargs)
    set_menu = kwargs.pop('set_menu', None)

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

    def new_folder(id=None, title=None, parent=parent,
                   view_id=view_id,
                   set_layout=set_layout,
                   get_layout=get_layout,
                   reindex=reindex,
                   reindexer=reindexer,
                   set_menu=set_menu,
                   **kwargs):
        created = False
        changed = False
        create = kwargs.pop('create', None)
        path = kwargs.pop('path', None)
        if create is None:
            create = bool(id or path)
        elif create:
            if not (id or path):
                raise TypeError('At least "id" or "path" is needed!')

        if id is None:
            if path is not None:
                logger.warn('Create or change %(path)r: '
                            'ignoring parent %(parent)r!',
                            locals())
                portal = getToolByName(parent, 'portal_url').getPortalObject()
                try:
                    new_child = portal.restrictedTraverse(_traversable_path(path))
                except KeyError:
                    logger.info('Object %(portal)r[%(path)r] not (yet) found!', locals())
                    new_child = None
        else:
            if path is not None:
                logger.warn('Looking for %(id)r in %(parent)r; '
                            'ignoring path %(path)r!',
                            locals())
            new_child = getattr(parent, id, None)

        if new_child is None and not create:
            logger.info('object not found (id=%(id)r, path=%(path)r, parent=%(parent)r', locals())
            return None

        if new_child is None:
            if id is None:  # in this case we have a path!
                chunks = normpath(path).split('/')
                id = chunks[-1]
                if not id:
                    raise ValueError('Empty id, and not really helpful path'
                            ' value! (%(path)r)'
                            % locals())
                parent = '/'.join(chunks[:-1])
                if parent in ('', '/'):
                    parent = portal
                else:
                    parent = portal.restrictedTraverse(_traversable_path(parent))

            if title is None:
                title = title_factory(id)
                logger.info('Default title for %(id)s is %(title)r', locals())
            logger.info('Creating folder %(parent)r/%(id)s (%(title)s)...',
                        locals())
            parent.manage_addFolder(id=id, title=title)
            new_child = getattr(parent, id)
            created = True
        elif title is not None:
            logger.info('Ignoring new title %(title)r for existing %(new_child)r',
                        locals())

        lognotes = make_notes_logger(logger)

        # ---------- [set_]language, [set_]canonical:
        ch, notes = handle_language(new_child, kwargs, created)
        # we don't have a changes counter here yet
        for tup in notes:
            lognotes(tup)
        if ch:
            changed = True

        # ---------- [set_]layout, view_id:
        if view_id is not None:
            kwargs['view_id'] = view_id
        kwargs.update(set_layout=set_layout, get_layout=get_layout)
        ch, notes, upd = handle_layout(new_child, kwargs, created)
        for tup in notes:
            lognotes(tup)
        if ch:
            changed = True

        # ---------- [set_]title:
        if not created:  # in this case we *have* set a title already
            if title is None:
                kwargs.update(default_title=title_factory(id))
            else:
                kwargs.update(title=title)
            ch, notes = handle_title(new_child, kwargs, created)
            for tup in notes:
                lognotes(tup)
            if ch:
                changed = True

        switch_menu = extract_menu_switch(kwargs, created)
        if switch_menu is not None:
            # see new function ._o_tools.handle_menu
            val = not switch_menu
            new_child.setExcludeFromNav(val)
            logger.info('%(new_child)r: setExcludeFromNav(%(val)r)', locals())
            changed = True  # TODO: use handle_menu

        uid = kwargs.pop('uid', None)
        if uid:
            logger.info('%(new_child)r: setting UID to %(uid)r', locals())
            new_child._setUID(uid)

        if reindex is None:
            reindex = (created
                       or changed
                       or reindexer is not None)
        if reindex and reindexer is None:
            reindexer = make_reindexer(logger=logger,
                                       context=parent)
        if reindex:
            res = reindexer(o=new_child)
            logger.info('%(res)r <-- reindexed %(new_child)r', locals())
        else:
            logger.info('NOT reindexed: %(new_child)r', locals())

        if kwargs:
            logger.warn('unused Arguments: %(kwargs)s', locals())
        return new_child

    return new_folder
