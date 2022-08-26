# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps")
"""

# Python compatibility:
from __future__ import absolute_import

__all__ = [
        ## _args (Helferlein für **kwargs):
        'extract_object_and_brain', # --> (o, brain)
        'extract_object_or_brain',  # --> (o, brain=None)
        'extract_brain_or_object',  # --> (brain, o=None)
        ## _attr:
        'make_attribute_setter',
        ## _decorator:
        'step',
        'StepAborted',
        ## _get_object:
        'make_object_getter',
        ## _make_folder:
        'make_subfolder_creator',
        ## _query:
        'make_query_extractor',
        'iterate_query',
        'getAllLanguages',
        ## _reindex:
        'make_reindexer',
        'reindex_all',
        ## _rename:
        # 'make_mover',  (noch nicht implementiert)
        'make_renamer',
        'ACCEPT_ANY',
        ## _roles:
        'set_local_roles',
        'make_simple_localroles_function',
        ## _switch:
        'switch_menu_item',  # Menüeintrag (de)aktivieren
        'show_item',
        'hide_item',
        ## _tree:
        'make_subfolder_creator',
        ## _types:
        'setVersionedTypes',  # --> setVersionableContentTypes
        ## _uid:
        'make_distinct_finder',
        'make_uid_setter',
        'make_uid_collector',
        ## _watch:
        'make_watcher_function',  # --> Signatur f(brain, string)
        ## _workflow:
        'make_transition_applicator',
        'load_and_cook',  # {css,js}registry.xml
        ## created by factory:
        'safe_context_id',
        ]
# Local imports:
from visaplan.plone.tools.setup._args import (
    extract_brain_or_object,
    extract_object_and_brain,
    extract_object_or_brain,
    )
from visaplan.plone.tools.setup._attr import make_attribute_setter
from visaplan.plone.tools.setup._decorator import StepAborted, step
from visaplan.plone.tools.setup._get_object import make_object_getter
from visaplan.plone.tools.setup._gs import load_and_cook, safe_context_id
from visaplan.plone.tools.setup._make_folder import make_subfolder_creator
from visaplan.plone.tools.setup._query import (
    getAllLanguages,
    iterate_query,
    make_query_extractor,
    )
from visaplan.plone.tools.setup._reindex import make_reindexer, reindex_all
from visaplan.plone.tools.setup._rename import ACCEPT_ANY, make_renamer
from visaplan.plone.tools.setup._roles import (
    make_simple_localroles_function,
    set_local_roles,
    )
from visaplan.plone.tools.setup._switch import (
    hide_item,
    show_item,
    switch_menu_item,
    )
from visaplan.plone.tools.setup._tree import clone_tree
from visaplan.plone.tools.setup._types import setVersionedTypes
from visaplan.plone.tools.setup._uid import (
    make_distinct_finder,
    make_uid_collector,
    make_uid_setter,
    )
from visaplan.plone.tools.setup._watch import make_watcher_function
from visaplan.plone.tools.setup._workflow import \
    make_transition_applicator  # TODO: transitions_map argument!
