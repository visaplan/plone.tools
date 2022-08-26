# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import, print_function

from six import iteritems as six_iteritems
from six import text_type as six_text_type

__all__ = [
    'split_group_id',
    'build_groups_set',
    ],

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

# ------------------------------------------------------- [ data ... [
# (from visaplan.plone.groups.unitraccgroups.utils)
# Die Reihenfolge ist wichtig!
STRUCTURE_GROUP_SUFFIXES = ['Reader', 'Author']

try:
    # visaplan:
    from visaplan.tools.classes import connected_dicts
except ImportError:
    if __name__ == '__main__':
        print('Dictionaries are not connected')
    else:
        raise
    _STRUCTURE_SUFFIX2ROLE = dict({
        'Author': 'Editor',
        'Reader': 'Reader',
    })
    _STRUCTURE_ROLE2SUFFIX = {}
    for key, val in _STRUCTURE_SUFFIX2ROLE.items():
        _STRUCTURE_ROLE2SUFFIX[val] = key
else:
    _STRUCTURE_SUFFIX2ROLE, _STRUCTURE_ROLE2SUFFIX = connected_dicts(**{
    'Author': 'Editor',
    'Reader': 'Reader',
    })
SUFFIX2ROLE = dict(_STRUCTURE_SUFFIX2ROLE)
SUFFIX2ROLE.update({
    'learner': 'Reader',
    # Die Alumni-Gruppe vermittelt keine Rolle
    # direkt auf dem betroffenen Objekt:
    'alumni': None,
    })
# -------------------------------- [ Gruppen für Kurse ... [
# Achtung, Kleinschreibung:
LEARNER_SUFFIX = intern('learner')
ALUMNI_SUFFIX = intern('alumni')
COURSE_GROUP_SUFFIXES = [LEARNER_SUFFIX, ALUMNI_SUFFIX]
# -------------------------------- ] ... Gruppen für Kurse ]
ALL_GROUP_SUFFIXES = STRUCTURE_GROUP_SUFFIXES + COURSE_GROUP_SUFFIXES
UID_CHARS = frozenset('0123456789abcdef')
SIMPLE_GROUP_INFO = {
        'uid': None,
        # das (z B. für 'Author') von der Rolle verschiedene *Suffix*:
        'role': None,
        }
RESOLVED_GROUP_INFO = {
        'uid': None,
        'suffix': None,
        'role': None,  # hier die real zuzuordnende Rolle
        }
PRETTY_MASK = {}
for role in ALL_GROUP_SUFFIXES:
    PRETTY_MASK[role] = u'%s group "{group}"' % role
if 0 and 'nur fuer den Parser':
    _('Author group "{group}"')
    _('Reader group "{group}"')
    _('learner group "{group}"')
    _('alumni group "{group}"')
# ------------------------------------------------------- ] ... data ]


def split_group_id(gid, resolve_role=False):
    """
    NOTE: This function is currently still quite specific;
          we might want to make it more general one day,
          e.g. using some more arguments.

    Splitte die übergebene Gruppen-ID auf und gib ein Dictionary zurück,
    das über eine etwaige "Rollenkomponente" informiert und dann auch
    die uid des zugehörigen Objekts enthält.

    Achtung:
        Der Schlüssel 'role' enthält bisher nicht wirklich den Namen der
        Rolle, sondern das Suffix, das von diesem in wichtigen Fällen abweicht!
        Um dies zu beheben, resolve_role=True übergeben;
        dies schreibt nach 'role' die *real zu verwendende* Rolle,
        und das Suffix steht im zusätzlichen Schlüssel 'suffix'.

        In einer späteren Version wird der Vorgabewert von resolve_role auf
        True geändert, und noch etwas später die Unterstützung für False
        entfernt.

    Zunächst die Tests für resolve_role=False:

    Die Schlüssel 'uid' und 'role' haben String-Werte,
    sofern der Mittelteil wie eine korrekte UID aussieht und das Suffix
    eine der hierfür bekannten Rollen ist;
    ansonsten sind sie None.

    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_Author')
    {'role': 'Author', 'uid': 'f6350ab731c3601e925eac482206bda5'}

    Bei "normalen" Gruppen hat die scheinbare (!) UID keine spezielle
    Bedeutung und wird daher nicht als solche zurückgegeben:

    >>> split_group_id('group_0123456789abcdef0123456789abcdef')
    {'role': None, 'uid': None}

    Das Suffix 'learner' repräsentiert keine echte Rolle (es wird stattdessen
    'Reader' vermittelt); es ist aber ein bekanntes Suffix
    und wird (mit resolve_role=False) als 'role' zurückgegeben
    (mit resolve_role=True als 'suffix'; siehe unten):

    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_learner')
    {'role': 'learner', 'uid': 'f6350ab731c3601e925eac482206bda5'}

    Wenn Unicode übergeben wird, kommt Unicode zurück:

    >>> split_group_id(u'group_f6350ab731c3601e925eac482206bda5_Author')
    {'role': u'Author', 'uid': u'f6350ab731c3601e925eac482206bda5'}

    Es wird genau auf Plausibilität geprüft und ggf. ein Dict. mit
    None-Werten zurückgegeben.

    Falsche Zeichen in der UID:
    >>> split_group_id('group_FOOBARBAZ1c3601e925eac482206bda5_Author')
    {'role': None, 'uid': None}

    Unbekanntes oder leeres Suffix:
    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_')
    {'role': None, 'uid': None}
    >>> split_group_id('group_f6350ab731c3601e925eac482206bda5_Foo')
    {'role': None, 'uid': None}

    Falsche Länge der UID:
    >>> split_group_id('group_f6350ab731c3601c482206bda5_Author')
    {'role': None, 'uid': None}

    Falsches Präfix:
    >>> split_group_id('gröup_f6350ab731c3601e925eac482206bda5_learner')
    {'role': None, 'uid': None}
    >>> split_group_id(u'gröup_f6350ab731c3601e925eac482206bda5_learner')
    {'role': None, 'uid': None}

    Nun ergänzend noch Tests für resolve_role=True:

    >>> def sgi(gid):
    ...     return sorted(split_group_id(gid, resolve_role=True).items())
    >>> sgi('group_0123456789abcdef0123456789abcdef')
    [('role', None), ('suffix', None), ('uid', None)]

    >>> sgi('group_f6350ab731c3601e925eac482206bda5_Reader')
    [('role', 'Reader'), ('suffix', 'Reader'), ('uid', 'f6350ab731c3601e925eac482206bda5')]
    >>> sgi('group_f6350ab731c3601e925eac482206bda5_Author')
    [('role', 'Editor'), ('suffix', 'Author'), ('uid', 'f6350ab731c3601e925eac482206bda5')]
    >>> sgi('group_f6350ab731c3601e925eac482206bda5_learner')
    [('role', 'Reader'), ('suffix', 'learner'), ('uid', 'f6350ab731c3601e925eac482206bda5')]

    Die Alumni-Gruppe vermittelt keine Rolle direkt auf dem betroffenen Objekt;
    daher ist die Rolle hier None:
    >>> sgi('group_f6350ab731c3601e925eac482206bda5_alumni')
    [('role', None), ('suffix', 'alumni'), ('uid', 'f6350ab731c3601e925eac482206bda5')]

    """
    liz = gid.split('_', 2)
    if resolve_role:
        res = dict(RESOLVED_GROUP_INFO)
    else:
        res = dict(SIMPLE_GROUP_INFO)

    if not liz[2:]:
        return res
    elif liz[0] != 'group':
        return res
    elif liz[2] not in ALL_GROUP_SUFFIXES:
        return res
    uid = liz[1]
    if not uid:
        return res
    elif set(uid).difference(UID_CHARS):
        return res
    elif len(uid) != 32:
        return res
    res['uid'] = uid
    if resolve_role:
        res['suffix'] = suffix = liz[2]
        res['role'] = SUFFIX2ROLE[suffix]
    else:
        res['role'] = liz[2]
    return res


def build_groups_set(dic, userid):
    """
    Hilfsfunktion für is_member_of_factory

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }
    >>> groups = build_groups_set(dic, 'user_a')
    >>> sorted(groups)
    ['group_a', 'group_b', 'user_a']
    """
    groups = set([userid])
    _traverse_dict(dic, groups)
    return groups


def _traverse_dict(dic, groups):
    """
    Hilfsfunktion für build_groups_set:
    realisiert die Rekursion.
    Es wird abgebrochen, wenn es keine Änderungen mehr gab.

    >>> dic = {'group_a': ['group_b', 'group_c'],
    ...        'group_b': ['user_a', 'user_b'],
    ...        'group_c': ['user_c'],
    ...        }

    <groups> enthält zunächst die <uid> (oder gid) selbst:
    >>> groups = set(['user_a'])

    Der Rückgabewert wird üblicherweise nicht verwendet;
    er gibt die Anzahl der Iterationen an:
    >>> _traverse_dict(dic, groups)
    2
    >>> sorted(groups)
    ['group_a', 'group_b', 'user_a']
    """
    iterations = 1
    while True:
        finished = True
        for gid, members in six_iteritems(dic):
            if gid in groups:
                continue
            if groups.intersection(members):
                groups.add(gid)
                finished = False
        if finished:
            break
        iterations += 1
    return iterations


if __name__ == '__main__':
    # Standard library:
    from doctest import testmod
    testmod()
