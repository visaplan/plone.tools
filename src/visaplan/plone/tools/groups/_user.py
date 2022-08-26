# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import, print_function

from six import text_type as six_text_type

from collections import defaultdict

# Zope:
from Products.CMFCore.utils import getToolByName

from visaplan.plone.tools.context import make_translator
from visaplan.tools.minifuncs import gimme_None

# Local imports:
from ._user_pio import _parse_init_options

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
def userinfo_factory(context, *args, **kwargs):
    """
    Wie groupinfo_factory, aber für Benutzerobjekte.

    pretty -- für Benutzer: title als formatierter Name
              (author.get_formatted_name), wenn möglich
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar
    missing -- return a dict for missing users as well,
               and add an `exists` key

    title_or_id -- für Verwendung mit visaplan.tools.classes.Proxy:
               gib nur den Title oder ersatzweise die ID zurück
               (mit pretty kombinierbar)
    """
    _parse_init_options(kwargs, args)
    pretty = kwargs['pretty']
    forlist = kwargs['forlist']
    missing = kwargs['missing']
    missing_mask = kwargs.get('missing_user_mask') or None
    title_or_id = kwargs['title_or_id']

    acl = getToolByName(context, 'acl_users')
    acl_gu = acl.getUser
    if pretty or not forlist:
        author = context.restrictedTraverse('@@author', None)
        gbbuid = author.getBrainByUserId
        gfn = author.get_formatted_name
    if missing:
        assert missing_mask
        translate = make_translator(context)
        missing_mask = translate(missing_mask)

    # ---------------------------- [ forlist ... [
    def basic_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, not: pretty
        """
        member = acl_gu(member_id)
        if member:
            res = {
                'id': member_id,
                'title': member.getProperty('fullname'),
                }
            if missing:
                res['exists'] = 1
            return res
        elif missing:
            return defaultdict(gimme_None,
                               id=member_id,
                               exists=0)
        else:
            return {}

    def pretty_user_info(member_id):
        """
        Basisinformationen über einen Benutzer:
        id, title

        forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            res = {
                'id': member_id,
                'title': (brain and gfn(brain))
                          or member.getProperty('fullname'),
                }
            if missing:
                res['exists'] = 1
        elif missing:
            res = defaultdict(gimme_None,
                              id=member_id,
                              exists=0)
            res['title'] = missing_mask.format(**res)
        else:
            return {}
        return res
    # ---------------------------- ] ... forlist ]

    # ------------------------ [ title_or_id ... [
    def pretty_title_or_id(member_id):
        dic = pretty_user_info(member_id)
        if dic or (missing and dic['exists']):
            return dic['title'] or member_id
        elif missing:
            return missing_mask.format(id=member_id)
        else:
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
            res = {
                'id': member_id,
                'title': member.getProperty('fullname'),
                'brain': brain,
                'email': member.getProperty('email'),
                }
            if missing:
                res['exists'] = 1
        elif missing:
            res = defaultdict(gimme_None,
                              id=member_id,
                              exists=0)
            res['title'] = missing_mask.format(**res)
        else:
            return {}
        return res

    def full_pretty_user_info(member_id):
        """
        not: forlist, pretty
        """
        member = acl_gu(member_id)
        if member:
            brain = gbbuid(member_id)
            res = {
                'id': member_id,
                'title': (brain and gfn(brain))
                         or member.getProperty('fullname'),
                'brain': brain,
                'email': member.getProperty('email'),
                }
            if missing:
                res['exists'] = 1
        elif missing:
            res = defaultdict(gimme_None,
                              id=member_id,
                              exists=0)
            res['title'] = missing_mask.format(**res)
        else:
            return {}
        return res

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
