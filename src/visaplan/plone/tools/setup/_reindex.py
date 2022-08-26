# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools for Product Setup (GS migration steps, "upgrade steps")

We provide a few convenience tools here, to help you avoid to rebuild
*all* metadata and indexes whenever your setup has changed,
regardless of the nature of the changes.

The reindexing method of the catalog always expects an indexes specification --
or None, which means: all indexes. So, what will we do if we don't really care
about the indexes because all our changes apply to metadata only?
We'll specify a "cheap" subset of the indexes;
this subset is taken from the registry (if collective.metadataversion is
installed; see below), with a hardcoded fallback value ['getId'].

To go a step further and monitor the metadata, using a metadata_version
metadata attribute, you might want to use collective.metadataversion,
which as well allows you to adjust this subset.
Because of the slightly changed focus, the function there is named differently
as well: .utils.make_metadata_updater.
"""

# Python compatibility:
from __future__ import absolute_import

# Setup tools:
import pkg_resources

try:
    pkg_resources.get_distribution('collective.metadataversion')
except pkg_resources.DistributionNotFound:
    HAVE_METADATAVERSION = 0
else:
    HAVE_METADATAVERSION = 1

# Standard library:
from traceback import extract_stack

try:
    # Zope:
    import transaction
    from Products.CMFCore.utils import getToolByName
    from ZODB.POSException import POSKeyError

    # Local imports:
    from visaplan.plone.tools.setup._query import make_query_extractor
except ImportError:
    if __name__ != '__main__':  # doctests
        raise
    print('WARNING: Some imports failed; some tests might fail as well')

# Logging / Debugging:
import logging
from pdb import set_trace
from visaplan.tools.debug import pp

__all__ = [
        'make_reindexer',
        'reindex_all',       # calls make_reindexer internally
        'get_default_idxs',  # return a cheap subset
        ]


if HAVE_METADATAVERSION:
    # Zope:
    from zope.component import getUtility

    # 3rd party:
    from collective.metadataversion.config import DEFAULT_IDXS, FULL_IDXS_KEY

    def get_default_idxs():
        """
        We have collective.metadataversion
        """
        registry = getUtility(IRegistry)
        val = list(registry.get(FULL_IDXS_KEY) or DEFAULT_IDXS)
        assert val, 'The default list of indexes must not be falsy!'
        return val
else:
    def get_default_idxs():
        """
        We DON'T have collective.metadataversion
        """
        return ['getId']


def _update_mri_kwargs(logger, kwargs):
    """
    Update a kwargs dict, asserting the presence of ``update_metadata`` and
    ``idxs`` keys.

    NOTE: This function is for internal use, and both the signature and
          the functionality may change without notice!

    We use a little test helper function here:

    >>> def umri(kwargs):
    ...     _update_mri_kwargs(None, kwargs)
    ...     return sorted(kwargs.items())

    The tests also assume our default list of "cheap indexes":
    >>> get_default_idxs()
    ['getId']

    By default, we update the metadata; unless explicitly specified,
    the indexes specification defaults to that cheap subset:
    >>> kw = dict()
    >>> umri(kw)
    [('idxs', ['getId']), ('update_metadata', 1)]
    >>> kw = dict(idxs=None)
    >>> umri(kw)
    [('idxs', None), ('update_metadata', 1)]
    >>> kw = dict(idxs='idx1 idx2'.split())
    >>> umri(kw)
    [('idxs', ['idx1', 'idx2']), ('update_metadata', 1)]

    However, you can always choose yourself whether to update the metadata,
    of course:
    >>> kw = dict(idxs=None, update_metadata=0)
    >>> umri(kw)
    [('idxs', None), ('update_metadata', 0)]
    >>> kw = dict(idxs='idx1 idx2'.split(), update_metadata=1)
    >>> umri(kw)
    [('idxs', ['idx1', 'idx2']), ('update_metadata', 1)]

    In fact, that `update_metadata` option "rules", if given,
    in affecting the default for the `idxs` option.
    >>> kw = dict(update_metadata=1)
    >>> umri(kw)
    [('idxs', ['getId']), ('update_metadata', 1)]
    >>> kw = dict(update_metadata=0)
    >>> umri(kw)
    [('idxs', None), ('update_metadata', 0)]

    You can explicitly specify update_metadata=None; in this case,
    it depends on the idxs specification:
    >>> kw = dict(update_metadata=None)
    >>> umri(kw)
    [('idxs', None), ('update_metadata', 0)]
    >>> kw = dict(idxs=None, update_metadata=None)
    >>> umri(kw)
    [('idxs', None), ('update_metadata', 0)]
    >>> kw = dict(idxs='idx1 idx2'.split(), update_metadata=None)
    >>> umri(kw)
    [('idxs', ['idx1', 'idx2']), ('update_metadata', 0)]
    >>> kw = dict(idxs=''.split(), update_metadata=None)
    >>> umri(kw)
    [('idxs', ['getId']), ('update_metadata', 1)]
    """
    changes = {}
    # The 'update_metadata' option "rules":
    if 'update_metadata' in kwargs:
        update_metadata = kwargs['update_metadata']
    else:
        update_metadata = 1
        changes.update({
            'update_metadata': update_metadata,
            })

    if 'idxs' in kwargs:
        idxs = kwargs['idxs']
        if update_metadata is None:  # must be specified explicitly
            if idxs is None:  # the known value for "all"
                update_metadata = 0
            elif not idxs:  # "no indexes" is not allowed!
                update_metadata = 1
                idxs = get_default_idxs()
                changes.update({
                    'idxs': idxs,
                    })
            else:
                # we have some "interesting subset" :
                update_metadata = 0
            changes.update({
                'update_metadata': update_metadata,
                })
        if isinstance(idxs, tuple):
            changes.update({
                'idxs': list(idxs),
                })
        elif idxs is None:
            pass
        elif not isinstance(idxs, list):
            changes.update({
                'idxs': idxs.split(),
                })
    elif update_metadata is None:
        # defaults: all indexes, no metadata
        changes.update({
            'idxs': None,
            'update_metadata': 0,
            })
    elif update_metadata:
        changes.update({
            'idxs': get_default_idxs(),
            'update_metadata': 1,
            })
    else:
        changes.update({
            'idxs': None,
            })
    kwargs.update(changes)


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
                      Wenn None, werden die Metadaten aktualisiert,
                      wenn eine leere Liste der Indexe übergeben wird.
    """
    pop = kwargs.pop
    logger = kwargs.pop('logger', None)
    if logger is None:
        logger = logging.getLogger('reindex')
    _update_mri_kwargs(logger, kwargs)
    update_metadata = kwargs.pop('update_metadata')
    ri_kwargs = {'update_metadata': update_metadata,
                 }
    idxs = kwargs.pop('idxs')
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
            except AttributeError as e:
                pp(('e:', e), ('brain:', brain), ('o:', o),
                   ('test:', repr(brain).startswith('<PloneSite ')))
                logger.error('KeyError %(e)r for brain (?!) %(brain)r', locals())
                if 0 and 'debug reindex':
                    set_trace()
                    pp(extract_stack())
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

        pt = getattr(o, 'portal_type', None)
        if pt == 'Plone Site':
            logger.warn("%(o)r: Won't reindex the site root", locals())
            return False

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


if __name__ == '__main__':
    # Standard library:
    import doctest
    doctest.testmod()
