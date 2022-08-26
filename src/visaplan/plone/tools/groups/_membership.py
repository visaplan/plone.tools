# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import

from six import text_type as six_text_type

# Zope:
from Products.CMFCore.utils import getToolByName

# visaplan:
from visaplan.tools.lands0 import list_of_strings

from ._helpers import build_groups_set

try:
    # visaplan:
    from visaplan.tools.coding import safe_decode
except ImportError:
    if __name__ != '__main__':
        raise
    def safe_decode(s):
        if isinstance(s, six_text_type):
            return s
        return s.decode('utf-8')

__all__ = [
    'is_direct_member__factory',
    'is_member_of__factory',
    'is_member_of_any',
    'get_all_members',
    'recursive_members',  # helper for get_all_members
    ]


def is_direct_member__factory(context, userid):
    """
    Erzeuge eine Funktion, die prüft, ob der *beim Erzeugen angegebene* Nutzer
    in der bei jedem Aufruf anzugebenden Gruppe direkt enthalten ist.
    """
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map

    def is_direct_member_of(group_id):
        return userid in gpm[group_id]

    return is_direct_member_of


def is_member_of__factory(context, userid):
    """
    Erzeuge eine Funktion, die die *direkte oder indirekte* Mitgliedschaft
    des übergebenen Users in der jeweils zu übergebenden Gruppe überprüft.
    """
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map

    groups = build_groups_set(gpm, userid)

    def is_member_of(groupid):
        return groupid in groups

    return is_member_of


def is_member_of_any(context, group_ids, user_id=None, default=False):
    """
    Is the given or active user member of one of the given groups?

    - For anonymous execution, raises Unauthorized
      (might become changable by keyword-only argument)
    - The normal usage is without specification of the user_id,
      i.e. checking for the logged-in user
    - if the group_ids sequence is empty, the default is used

    """
    pm = getToolByName(context, 'portal_membership')
    if pm.isAnonymousUser():
        raise Unauthorized
    if user_id is not None:
        # wer darf sowas fragen? Manager, Gruppenmanager, ...?
        # TODO: Hier entsprechende Überprüfung!
        pass

    if not group_ids:
        return default
    if user_id is None:
        member = pm.getAuthenticatedMember()
        user_id = member.getId()

    return user_id in get_all_members(context, group_ids)


def get_all_members(context, group_ids, **kwargs):  # --- [[
    """
    Return all members of the given groups

    Liefere alle Mitglieder der übergebenen Gruppe(n).

    Schlüsselwortargumente für .utils.recursive_members und
    groupinfo_factory dürfen angegeben werden;
    letztere werden aber ignoriert, wenn die vorgabegemäße Filterung
    groups_only=True übersteuert wird. In diesem Fall (potentiell sowohl
    Benutzer als auch Gruppen, oder nur Benutzer) werden nur IDs
    zurückgegeben.

    Rückgabe:
    - Sequenz von Gruppeninformationen, mit groups_only=True (Vorgabe);
    - ansonsten nur eine Sequenz der IDs (je nach Aufrufargumenten nur
      Benutzer-IDs, oder gemischt)
    """
    acl = getToolByName(context, 'acl_users')
    gpm = acl.source_groups._group_principal_map
    filter_args = {}
    for key in ('groups_only', 'users_only',
                'containers',
                'default_to_all'):
        try:
            filter_args[key] = kwargs.pop(key)
        except KeyError:
            pass
    members = recursive_members(list_of_strings(group_ids),
                                gpm, **filter_args)
    groups_only = filter_args.get('groups_only', False)
    if groups_only:
        format_args = {'pretty': False,
                       'forlist': True,
                       'missing': 1,
                       }
        format_args.update(kwargs)
        ggibi = groupinfo_factory(context, **format_args)
        res = []
        for gid in members:
            res.append(ggibi(gid))
        return res
    elif kwargs and debug_active:
        pp('ignoriere:', kwargs)

    return members
# ---------------------------------- ] ... get_all_members ]


def recursive_members(gids, dic,
                      containers=None,
                      groups_only=False,
                      users_only=False,
                      default_to_all=False):
    """
    Recursively find all members of the (by id) given groups.

    Mandatory arguments:

      gids -- group ids; a sequence or (for convenience) a string
              (which would be split by whitespace)
      dic -- a dictionary; usually acl.source_groups._group_principal_map

    Ermittle die rekursiv aufgelösten Mitglieder der übergebenen
    Gruppen.

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        'group_d': ['group_a'],
    ...        }
    >>> am = recursive_members(['group_a'], dic, groups_only=True)
    >>> sorted(am)
    ['group_b', 'group_c']
    >>> sorted(recursive_members(['group_a'], dic))
    ['group_b', 'group_c', 'user_a', 'user_b', 'user_c']
    >>> sorted(recursive_members(['group_d'], dic, users_only=True))
    ['user_a', 'user_b', 'user_c']
    >>> sorted(recursive_members(['group_d'], dic, groups_only=True))
    ['group_a', 'group_b', 'group_c']

    containers-Argument:
    - True: die Container werden hinzugefügt
      (mit groups_only: ... sofern es wirklich Gruppen sind)
    - False: die Container werden ausgefiltert
    - None (Vorgabe): weder aktiv hinzufügen noch ausfiltern

    >>> kwargs = {'groups_only': True,
    ...           'containers': True}
    >>> sorted(recursive_members(['group_d'], dic, **kwargs))
    ['group_a', 'group_b', 'group_c', 'group_d']
    >>> kwargs = {'groups_only': True,
    ...           'containers': False}
    >>> sorted(recursive_members(['group_c', 'group_d'], dic, **kwargs))
    ['group_a', 'group_b']
    >>> kwargs = {'users_only': True,
    ...           'containers': True}
    >>> sorted(recursive_members(['group_d'], dic, **kwargs))
    ['user_a', 'user_b', 'user_c']
    >>> kwargs = {'containers': False}

    Das spezielle Argument default_to_all erfordert groups_only=True
    und gibt alle Gruppen zurück, sofern keine Gruppen-IDs übergeben wurden:

    >>> sorted(recursive_members([], dic, groups_only=True,
    ...                          default_to_all=True))
    ['group_a', 'group_b', 'group_c', 'group_d']
    """
    if users_only and groups_only:
        raise ValueError('recursive_members(%(gids)r): '
                         '*either* groups_only '
                         '*or* users_only!'
                         % locals())
    if not gids:
        if default_to_all:
            assert groups_only, 'default_to_all erfordert groups_only!'
            return set(dic.keys())
        else:
            # ohne default_to_all: keine Gruppen, keine Mitglieder
            return set()
    filtered = users_only or groups_only
    res = set()
    exclude = set()
    if containers is None:
        pass
    elif not containers:
        exclude.update(gids)
    for gid in gids:
        try:
            newly_found = set(dic[gid]).difference(res)
            if containers and not users_only:
                res.add(gid)
        except KeyError:  # keine Gruppe, oder?!
            if containers and not groups_only:
                res.add(gid)
        else:
            while newly_found:
                res.update(newly_found)
                this_iteration = set()
                for mid in newly_found:  # member id
                    try:
                        found_here = set(dic[mid]).difference(res)
                        if found_here:
                            this_iteration.update(found_here)
                        if users_only:   # Gruppen aus Ergebnis entfernen
                            exclude.add(mid)
                    except KeyError:
                        if groups_only:  # Benutzer aus Ergebnis entfernen
                            exclude.add(mid)
                res.update(this_iteration)
                newly_found = this_iteration
    res.difference_update(exclude)
    return res

