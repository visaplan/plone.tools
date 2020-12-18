# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _tree
"""

# Python compatibility:
from __future__ import absolute_import

# Zope:
import transaction
from Products.CMFCore.utils import getToolByName
from ZODB.POSException import POSKeyError

# Local imports:
from visaplan.plone.tools.setup._query import make_query_extractor

# Logging / Debugging:
import logging
from pdb import set_trace
from visaplan.tools.debug import pp

__all__ = [
        'make_reindexer',
        'reindex_all',
        ]


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

    update_metadata - sollen die Metadaten aktualisiert werden?
                      (Vorgabe: True)
                      Wenn None, werden die Metadaten aktualisiert,
                      wenn eine leere Liste der Indexe übergeben wird.
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
        Reindex the given object (by default given as brain!)

        If computing the object yourself, don't give the brain
        but specify the object by name: reindex(o=theobject).
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
            if o2 != o:  # check for identity was too strict!
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


def reindex_all(**kwargs):
    """
    Reindiziere die angegebenen Objekte.

    Mögliche benannte Argumente:

    - von make_query_extractor() extrahierte Suchparameter,
      als da wären

      - getCustomSearch
      - getExcludeFromSearch
      - Language
      - path
      - portal_type

    - Argumente zum Erzeugen eines Reindexers

    ...
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
