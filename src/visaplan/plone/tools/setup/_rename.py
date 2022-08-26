# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _rename
"""

# Python compatibility:
# Plone, sonstiges:
from __future__ import absolute_import

# Zope:
from Products.CMFCore.utils import getToolByName

__all__ = [
        # 'make_mover',  (not yet implemented)
        'make_renamer',
        # data:
        'ACCEPT_ANY',
        ]


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
                    #    oldpath = '/'.join(o.getPhysicalPath())
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

