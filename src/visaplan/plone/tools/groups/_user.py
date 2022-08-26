# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import, print_function

from six import text_type as six_text_type

# Zope:
from Products.CMFCore.utils import getToolByName

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
    'userinfo_factory',
    ]


# --------------------------------- [ userinfo_factory ... [
def userinfo_factory(context, pretty=0, forlist=0,
                     title_or_id=0):
    """
    Wie groupinfo_factory, aber für Benutzerobjekte.

    pretty -- für Benutzer: title als formatierter Name
              (author.get_formatted_name), wenn möglich
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar
    title_or_id -- für Verwendung mit visaplan.tools.classes.Proxy:
               gib nur den Title oder ersatzweise die ID zurück
               (mit pretty kombinierbar)
    """
    acl = getToolByName(context, 'acl_users')
    acl_gu = acl.getUser
    if pretty or not forlist:
        author = context.restrictedTraverse('@@author', None)
        gbbuid = author.getBrainByUserId
        gfn = author.get_formatted_name

    # ---------------------------- [ forlist ... [
    def basic_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, not: pretty
        """
        member = acl_gu(member_id)
        if member:
            return {'id': member_id,
                    'title': member.getProperty('fullname'),
                    }

    def pretty_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': (brain and gfn(brain))
                             or member.getProperty('fullname'),
                    }
    # ---------------------------- ] ... forlist ]

    # ------------------------ [ title_or_id ... [
    def pretty_title_or_id(member_id):
        try:
            return pretty_user_info(member_id)['title'] \
                   or member_id
        except:
            return None

    def basic_title_or_id(member_id):
        try:
            return basic_user_info(member_id)['title'] \
                   or member_id
        except:
            return None
    # ------------------------ ] ... title_or_id ]

    def full_user_info(member_id):
        """
        not: forlist, not: pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': member.getProperty('fullname'),
                    'brain': brain,
                    'email': member.getProperty('email'),
                    }

    def full_pretty_user_info(member_id):
        """
        not: forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            return {'id': member_id,
                    'title': (brain and gfn(brain))
                             or member.getProperty('fullname'),
                    'brain': brain,
                    'email': member.getProperty('email'),
                    }

    if title_or_id:
        if pretty:
            return pretty_title_or_id
        else:
            return basic_title_or_id
    if forlist:
        if pretty:
            return pretty_user_info
        else:
            return basic_user_info
    if pretty:
        return full_pretty_user_info
    else:
        return full_user_info
# --------------------------------- ] ... userinfo_factory ]
