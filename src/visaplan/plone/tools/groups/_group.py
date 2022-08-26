# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import, print_function

from six import text_type as six_text_type

from collections import defaultdict

# Zope:
from Products.CMFCore.utils import getToolByName

from visaplan.tools.minifuncs import gimme_None

# Local imports:
from ._data import PRETTY_MASK
from ._group_pio import _parse_init_options
# since this function uses some quite application specific data,
# it is a hot candidate for an initialiation option:
from ._helpers import split_group_id
from visaplan.plone.tools.context import make_translator, getbrain

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

try:
    # visaplan:
    from visaplan.plone.groups.unitraccgroups.utils import pretty_group_title
except ImportError:
    if __name__ != '__main__':
        raise
    print("E: Couldn't import pretty_group_title!")
    pretty_group_title = None


__all__ = [
    'groupinfo_factory',
    ]


# -------------------------------- [ groupinfo_factory ... [
def groupinfo_factory(context, *args, **kwargs):
    """
    Factory-Funktion; als Ersatz für get_group_info_by_id, insbesondere für
    wiederholte Aufrufe.  Indirektionen etc. werden einmalig beim Erstellen der
    Funktion aufgelöst und anschließend in einer Closure vorgehalten.

    Historisch wurden die Optionen pretty, forlist und searchtext auch
    (in dieser Reihenfolge) positional akzeptiert; dies wird nicht mehr empfohlen
    (wenn auch durch _parse_init_options derzeit noch unterstützt):

    pretty -- Gruppennamen auflösen, wenn Suffix an ID und Titel
    forlist -- Minimale Rückgabe (nur ID und Titel),
               aber mit pretty kombinierbar
    missing -- return a dict for missing groups as well,
               and add an `exists` key

    searchtext -- Erzeuge eine Funktion, um einen Suchtext zu erzeugen;
                  diese nimmt keinee Gruppen-ID entgegen (wie die andernfalls
                  erzeugten Funktionen), sondern ein von diesen erzeugtes
                  Info-Dict.
    """
    _parse_init_options(kwargs, args)
    pretty = kwargs['pretty']
    if pretty_group_title is None and pretty:
        raise ValueError('pretty=%(pretty)r not supported; '
                "Couldn't import from visaplan.plone.groups!"
                % kwargs)
    forlist = kwargs['forlist']
    missing = kwargs['missing']
    missing_mask = kwargs.get('missing_group_mask') or None
    searchtext = kwargs['searchtext']

    acl = getToolByName(context, 'acl_users')
    pg = getToolByName(context, 'portal_groups')
    get_group = pg.getGroupById
    translate = make_translator(context)
    GROUPS = acl.source_groups._groups
    if missing:
        missing_mask = translate(missing_mask)

    def minimal_group_info(group_id):
        """
        Return a dict with keys 'id', 'group_title', or empty.
        """
        group = get_group(group_id)

        try:
            thegroup = GROUPS[group_id]
        except KeyError:
            if missing:
                return defaultdict(gimme_None,
                                   id=group_id,
                                   exists=0)
            return {}
        else:
            dict_ = {
                'id': group_id,
                'group_title': safe_decode(thegroup['title']),
                }
            if missing:
                dict_['exists'] = 1
            return dict_

    def basic_group_info(group_id):
        """
        Gib ein Dict. zurück;
        - immer vorhandene Schlüssel:
          id, group_title, group_description, group_manager, group_desktop
        - nur bei automatisch erzeugten Gruppen: role, role_translation, brain

        Argumente:
        group_id -- ein String, normalerweise mit 'group_' beginnend
        """

        group = get_group(group_id)

        try:
            thegroup = GROUPS[group_id]
        except KeyError:
            if missing:
                return defaultdict(gimme_None,
                                   id=group_id,
                                   exists=0)
            return {}
        else:
            dict_ = {
                'id': group_id,
                'group_title': safe_decode(thegroup['title']),
                }
            if missing:
                dict_['exists'] = 1

        # propietary keys:
        dict_['group_description'] = safe_decode(thegroup['description'])
        dict_['group_manager'] = thegroup.get('group_manager')
        dict_['group_desktop'] = thegroup.get('group_desktop')

        dic = split_group_id(group_id)
        if dic['role'] is not None:
            dict_.update(dic)

        # refered object (for <group_><uid>[_role]:
        dict_['role_translation'] = translate(dic['role'])  # local role-to-be-mapped
        dict_['brain'] = getbrain(context, dic['uid'])  # refered object
        return dict_

    def pretty_group_info(group_id):
        """
        Ruft basic_group_info auf und fügt einen Schlüssel 'pretty_title'
        hinzu, der den Gruppentitel ohne das Rollensuffix enthält.
        """
        dic = basic_group_info(group_id)
        if not dic:
            assert not missing
            return dic
        elif not dic.get('exists', 1):
            assert missing
            if 'group_id' in missing_mask:
                dic['group_id'] = group_id
            dic['pretty_title'] = missing_mask.format(**dic)
            return dic

        if 'role' not in dic:
            dic['pretty_title'] = translate(dic['group_title'])
            return dic
        liz = dic['group_title'].split()
        if liz and liz[-1] == dic['role']:
            stem = u' '.join(liz[:-1])
            mask = PRETTY_MASK[dic['role']]
            dic['pretty_title'] = translate(mask).format(group=stem)
        else:
            dic['pretty_title'] = translate(dic['group_title'])
        return dic

    def minimal2_group_info(group_id):
        """
        Ruft minimal_group_info auf und modifiziert ggf. den Schlüssel
        'group_title' (entsprechend dem von pretty_group_info zurückgegebenen
        Schlüssel 'pretty_title')
        """
        dic = minimal_group_info(group_id)
        if not dic:
            assert not missing
            return dic
        elif not dic.get('exists', 1):
            assert missing
            return dic

        dic2 = split_group_id(group_id)
        if dic2['role'] is not None:
            dic.update(dic2)
        if 'role' not in dic:
            dic['group_title'] = translate(dic['group_title'])
            return dic
        liz = dic['group_title'].split()
        if liz and liz[-1] == six_text_type(dic['role']):
            stem = u' '.join(liz[:-1])
            mask = PRETTY_MASK[dic['role']]
            dic['group_title'] = translate(mask).format(group=stem)
        else:
            dic['group_title'] = translate(dic['group_title'])
        return dic

    def make_searchstring(group_info):
        """
        Arbeite direkt auf einem group_info-Dict;
        Gib kein Dict zurück, sondern einen String für Suchzwecke
        """
        try:
            group_id = group_info['id']
        except KeyError:
            raise
        try:
            res = [safe_decode(group_info['title']),
                   safe_decode(group_id)]
        except KeyError:
            print(list(group_info.items()))
            raise
            return u''
        dic2 = split_group_id(group_id)
        prettify = True
        for val in dic2.values():
            if val is None:
                prettify = False
                break  # es sind immer alle None, oder alle nicht None
            else:
                res.append(safe_decode(val))
        if prettify:
            pretty = pretty_group_title(group_id, res[0], translate)
            if pretty is not None:
                res.append(safe_decode(pretty))
        descr = group_info['description']
        if descr:
            res.append(safe_decode(descr))
        return u' '.join(res)

    if searchtext:
        return make_searchstring
    if forlist:
        if pretty:
            return minimal2_group_info
        else:
            return minimal_group_info
    if pretty:
        return pretty_group_info
    else:
        return basic_group_info
# -------------------------------- ] ... groupinfo_factory ]
