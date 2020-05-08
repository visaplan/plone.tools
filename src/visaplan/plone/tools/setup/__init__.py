# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps")
"""

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
        ]
from ._args import (
        extract_object_and_brain, extract_object_or_brain,
        extract_brain_or_object,
        )
from ._attr import (
        make_attribute_setter,
        )
from ._decorator import (
        step, StepAborted,
        )
from ._get_object import (
        make_object_getter,
        )
from ._make_folder import (
        make_subfolder_creator,
        )
from ._query import (
        make_query_extractor, iterate_query,
        getAllLanguages,
        )
from ._reindex import (
        make_reindexer, reindex_all,
        )
from ._rename import (
        make_renamer, ACCEPT_ANY,
        )
from ._roles import (
        make_simple_localroles_function, set_local_roles,
        )
from ._switch import (
        switch_menu_item, show_item, hide_item,
        )
from ._tree import (
        clone_tree,
        )
from ._types import (
        setVersionedTypes,
        )
from ._uid import (
        make_distinct_finder, make_uid_setter, make_uid_collector,
        )
from ._watch import (
        make_watcher_function,
        )
from ._workflow import (
        make_transition_applicator,  # TODO: transitions_map argument!
        )
