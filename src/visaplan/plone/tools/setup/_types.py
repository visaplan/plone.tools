# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _types
"""

# Python compatibility:
from __future__ import absolute_import

# Zope:
from Products.CMFCore.utils import getToolByName

# Logging / Debugging:
import logging

__all__ = [
        'setVersionedTypes',
        ]


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
