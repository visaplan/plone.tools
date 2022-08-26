# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Tools für Produkt-Setup (Migrationsschritte, "upgrade steps"): _roles
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types

# visaplan:
from visaplan.tools.classes import Proxy

# Local imports:
from visaplan.plone.tools.setup._args import extract_object_and_brain

__all__ = [
        'make_simple_localroles_function',
        'set_local_roles',
        ]


def make_simple_localroles_function(**kwargs):
    """
    Erzeuge eine einfache Funktion, um (hier: ohne Differenzierung nach
    portal_type ö.ä.) für alle Objekte mit dem angegeben Workflow-Zielstatus
    <target_state> die lokalen Rollen <roles> für den Prinzipal <userid>
    zuzuweisen; die Funktion set_local_roles wird dies dann so interpretieren,
    daß etwaige schon vorhandene weitere lokale Rollen erhalten bleiben.
    """
    for_target_state = kwargs.pop('target_state', 'restricted')
    userid = kwargs.pop('userid')
    roles = kwargs.pop('roles')
    add = kwargs.pop('add', True)
    if isinstance(roles, six_string_types):
        roles = [roles]
    def new_local_roles(brain, target_state):
        if target_state == for_target_state:
            return [(userid, roles, add)]
        return []
    return new_local_roles


def set_local_roles(**kwargs):
    """
    Modifiziere die lokalen Rollenzuweisungen des übergebenen Objekts

    Argumente, alle benannt zu übergeben:

    o -- das Objekt
    brain -- dessen Indexobjekt
             (eines der beiden muß angegeben werden)

    logger -- der Logger

    func -- Eine Funktion, die aus <brain> und <target_state> eine Liste mit
            den gewünschten Änderungen ermittelt (wie <thelist>);
            siehe make_simple_localroles_function
    target_state -- nur zur Übergabe an <func>

    thelist -- eine Liste von (userid, roles [, add])-Tupeln;
               nur benötigt (und verwendet), wenn <func> nicht angegeben

    Von diesen wird zwingend benötigt:
    - logger
    - mindestens eines von o und brain
      (keine explizite Prüfung; es wird aber ggf. ein Fehler auftreten)
    - alternativ:
      - func und target_state, um die zu setzenden oder zu löschenden
        Rollen mit Hilfe der Funktion <func> zu ermitteln;
        oder:
      - thelist
        (derzeit ignoriert, wenn <func> übergeben wurde und nicht None ist)
    """
    o, brain = extract_object_and_brain(kwargs)
    # if 'func' in kwargs:
    func = kwargs.pop('func', None)
    if func is not None:
        # wird benötigt, als Argument für die Funktion!
        target_state = kwargs.pop('target_state')
        thelist = func(brain, target_state)
    else:
        thelist = kwargs.pop('thelist')
    logger = kwargs.pop('logger')
    if not thelist:
        return False
    uid = brain.UID
    changes = 0
    def set_of_roles(userid):
        return set(o.get_local_roles_for_userid(userid=userid))

    roles_of_user = Proxy(set_of_roles)
    changed_users = set()
    for tup in thelist:
        userid, roles = tup[:2]
        if isinstance(roles, six_string_types):
            roles = [roles]
        if tup[2:]:
            tail = tup[3:]
            if tail:
                logger.warn('set_local_roles: %(tup)r is too long'
                            '; ignoring %(tail)r',
                            locals())
            add = tup[2]
            if add not in (True, False,
                           1, 0,  # pep 20.2
                           ):
                txt = ('set_local_roles: %(tup)r contains wrong 3rd value'
                       ' %(add)r; boolean expected'
                       ) % locals()
                logger.error(txt)
                raise ValueError(txt)
        else:
            add = True

        for role in roles:
            roles_set = roles_of_user[userid]
            if role in roles_set:
                if add:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' %(role)r already found (%(o)r)', locals())
                else:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' removing %(role)r (%(o)r)', locals())
                    roles_set.discard(role)
                    changed_users.add(userid)
            else:
                if add:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' adding %(role)r (%(o)r)', locals())
                    changed_users.add(userid)
                    roles_set.add(role)
                else:
                    logger.info('%(uid)r local roles for %(userid)r:'
                                ' %(role)r not found (%(o)r)', locals())

    if not changed_users:
        return False
    done_users = set()
    for userid in sorted(changed_users):
        roles_set = roles_of_user[userid]
        if roles_set:
            sorted_roles = sorted(roles_set)
            logger.info('%(uid)r local roles for %(userid)r:'
                        ' set to %(sorted_roles)s (%(o)r)', locals())
            o.manage_setLocalRoles(userid, sorted_roles)
            done_users.add(userid)
    changed_users.difference_update(done_users)
    if changed_users:
        userids = sorted(changed_users)
        logger.info('%(uid)r local roles for %(userids)s:'
                    ' removing all roles (%(o)r)', locals())
        o.manage_delLocalRoles(userids)
    o.reindexObjectSecurity()
    return True

