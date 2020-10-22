# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _query
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types

# Zope:
from Products.CMFCore.utils import getToolByName

# Logging / Debugging:
import logging

__all__ = [
        'make_query_extractor',
        'iterate_query',
        'getAllLanguages',
        ]


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
                if isinstance(val, six_string_types):
                    val = [val]
                query[name] = val
        # Vorgabe: alle aktiven Sprachen
        Language = pop('Language', None)
        if Language is None:
            Language = getAllLanguages(context)
        # https://docs.plone.org/develop/plone/searching_and_indexing/query.html#bypassing-language-check:
        if isinstance(Language, six_string_types) and Language != 'all':
            Language = [Language]
        query['Language'] = Language
        return query
    return extract_query


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


def getAllLanguages(context, exclude=[]):
    """
    Zur Suche nach allen Sprachen (Index: "Language"),
    um keine Objekte zu verfehlen
    """
    language_tool = getToolByName(context, 'portal_languages')
    langs = sorted([x[0] for x in language_tool.listSupportedLanguages()])
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
