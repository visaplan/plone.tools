# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Standardmodule
from string import capitalize
from posixpath import normpath

# Plone, sonstiges:
from Products.CMFCore.utils import getToolByName

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
from ._misc import (
        _traversable_path,
        make_title,
        )
from ._o_tools import (
        handle_language,
        handle_menu,
        handle_title,
        make_notes_logger,
        )

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

    switch_menu - True übergeben, um den neuen (oder schon existierenden)
                  Ordner explizit der Navigation hinzuzufügen
                  (es wird auch "menu" verstanden; wenn beide angegeben,
                  ungleich und ungleich None sind, gibt es einen Konflikt)
    parent - das schon existierende ordnerartige Elternobjekt
    view_id - die ID der aufzuschaltenden Ansicht
    """
    parent = kwargs.pop('parent', None)
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('new folder')
    title_factory = kwargs.pop('title_factory', None)
    if title_factory is None:
        title_factory = make_title
    view_id, set_layout, get_layout = extract_layout_switch(kwargs)
    switch_menu_default = extract_menu_switch(kwargs)
    reindexer = kwargs.pop('reindexer', None)
    if switch_menu_default is not None:
        reindex = kwargs.pop('reindex', True)
    else:
        reindex = kwargs.pop('reindex', reindexer is not None
                                        or None)

    def new_folder(id=None, title=None, parent=parent,
                   view_id=view_id,
                   set_layout=set_layout,
                   get_layout=get_layout,
                   reindex=reindex,
                   reindexer=reindexer,
                   **kwargs):
        created = False
        switch_menu = extract_menu_switch(kwargs, switch_menu_default)
        if id is None:
            path = kwargs.pop('path', None)
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
                raise TypeError('At least "id" or "path" is needed!')
        else:
            new_child = getattr(parent, id, None)

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

        # ---------- [set_]layout, view_id:
        if view_id is not None:
            kwargs['view_id'] = view_id
        kwargs.update(set_layout=set_layout, get_layout=get_layout)
        ch, notes, upd = handle_layout(o, kwargs, created)
        changes += ch
        for tup in notes:
            lognotes(tup)

        # ---------- [set_]title:
        if not created:  # in this case we *have* set a title already
            if title is None:
                kwargs.update(default_title=title_factory(id))
            else:
                kwargs.update(title=title)
            ch, notes = handle_title(new_child, kwargs, created)
            for tup in notes:
                lognotes(tup)

        if switch_menu is not None:
            # see new function ._o_tools.handle_menu
            val = not switch_menu
            new_child.setExcludeFromNav(val)
            logger.info('%(new_child)r: setExcludeFromNav(%(val)r)', locals())
            if reindex and reindexer is None:
                reindexer = make_reindexer(logger=logger,
                                           context=parent)
        elif reindex is None:
            reindex = reindexer is not None

        uid = kwargs.pop('uid', None)
        if uid:
            logger.info('%(new_child)r: setting UID to %(uid)r', locals())
            new_child._setUID(uid)
        if reindex:
            # import pdb; pdb.set_trace()
            reindexer(o=new_child)

        if kwargs:
            logger.warn('unused Arguments: %(kwargs)s', locals())
        return new_child

    return new_folder