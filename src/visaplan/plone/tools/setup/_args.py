# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Helpers for arguments exploitation
"""

__all__ = [
        # Helferlein für **kwargs:
        'extract_object_and_brain', # --> (o, brain)
        'extract_object_or_brain',  # --> (o, brain=None)
        'extract_brain_or_object',  # --> (brain, o=None)
        # [switch_]menu:
        'extract_menu_switch',
        'extract_layout_switch',
        ]


def extract_object_or_brain(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (o, brain) zurück.

    Der Zweck ist die Ermittlung des Objekts; wenn 'brain' nicht enthalten ist,
    wird hierfür None zurückgegeben.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt

    >>> dic1 = {'brain': MockBrain(), 'other': 1}
    >>> extract_object_or_brain(dic1)
    (<an object>, <a brain>)
    >>> dic1
    {'other': 1}
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
        if o is None:
            o = brain.getObject()
    else:
        o = get('o')
        brain = None
    return o, brain


def extract_object_and_brain(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (o, brain) zurück.

    Das jeweils fehlende wird ermittelt; eines von beiden muß natürlich
    enthalten sein.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt

    >>> dic11 = {'brain': MockBrain(), 'other': 11}
    >>> extract_object_and_brain(dic11)
    (<an object>, <a brain>)
    >>> dic11
    {'other': 11}
    >>> dic12 = {'o': MockObject(), 'other': 12}
    >>> extract_object_and_brain(dic12)
    (<an object>, <a brain>)
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
        if o is None:
            o = brain.getObject()
    else:
        o = get('o')
        brain = None
    if brain is None:
        brain = o.getHereAsBrain()
    return o, brain


def extract_brain_or_object(dic, do_pop=True):
    """
    Extrahiere die Schlüssel 'o' (ein Objekt) und 'brain' aus dem übergebenen
    Dict; gib ein 2-Tupel (brain, o) zurück.

    Der Zweck ist die Ermittlung des 'Brains'; wenn 'o' nicht enthalten ist,
    wird hierfür None zurückgegeben.

    dic -- das Python-Dict-Objekt
    do_pop -- wenn True (Vorgabe), werden die Schlüssel aus dem Dict entfernt

    Wenn das 'brain' schon enthalten ist, braucht das Objekt nicht beschafft zu
    werden:
    >>> dic21 = {'brain': MockBrain(), 'other': 21}
    >>> extract_brain_or_object(dic21)
    (<a brain>, None)
    >>> dic21
    {'other': 21}

    >>> dic22 = {'o': MockObject(), 'other': 22}
    >>> extract_brain_or_object(dic22)
    (<a brain>, <an object>)
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    if 'brain' in dic:
        brain = get('brain')
        if 'o' in dic:
            o = get('o', None)
        else:
            o = None
    else:
        o = get('o')
        brain = None
    if brain is None:
        brain = o.getHereAsBrain()
    return brain, o


def extract_menu_switch(dic, default=None, do_pop=True):
    """
    Extract the switch_menu and/or menu (boolean) value
    from the given dict; if both are present but different,
    a ValueError is raised.

    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    res = None
    keys = []
    for key in (
        'switch_menu', 'menu',
        ):
        val = get(key, None)
        if val is not None:
            if res is None:
                res = val
            elif val != res:
                earlier = keys[1:] and tuple(keys) or keys[0]
                raise ValueError('%(key)r: %(val)r conflicts '
                                 '%(earlier)r value %(res)r!'
                                 % locals())
            keys.append(key)
    if res is None:
        return default
    return res


def extract_layout_switch(dic, default=None, do_pop=True):
    """
    Extract the layout and/or view_id value
    from the given dict; if both are present but different,
    a ValueError is raised.

    Futhermore, the "layout" might be got (.getLayout) or set
    (.selectViewTemplate);
    thus, a 3-tuple ('layout_id', do_set, do_get) is returned.
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    layout = None
    layout_given = False
    set_given = 'set_layout' in dic
    set_layout = get('set_layout', None)
    get_given = 'get_layout' in dic
    get_layout = get('get_layout', None)
    keys = []
    for key in (
        'layout', 'view_id',
        ):
        val = get(key, None)
        if val is not None:
            if layout is None:
                layout = val
            elif val != layout:
                earlier = keys[1:] and tuple(keys) or keys[0]
                raise ValueError('%(key)r: %(val)r conflicts '
                                 '%(earlier)r value %(layout)r!'
                                 % locals())
            keys.append(key)
            layout_given = True
    if layout is None:
        layout = default

    if set_layout is None:
        set_layout = bool(layout)

    return (layout, set_layout, get_layout)


def _extract_move_args(dic, default=None, do_pop=True):
    """
    Only for _tree.clone_tree for now, and not yet generalized;
    might become replaced, removed or renamed!

    Take a (usually: **kwargs) dict and extract (by default: pop)
    the keys move_children, move_limit and move_limit_each

    Return a 3-tuple (move_children, move_limit, move_limit_each);
    move_children defaults to True, if at least one of the other keys
    were contained.

    Arguments:

    dic - the dictionary
    default - default value for move_limit* keys
    do_pop - whether to pop the keys from the dict.

    >>> dic = {'move_limit': 1, 'other_option': 42}
    >>> _extract_move_args(dic)
    (True, 1, None)
    >>> dic
    {'other_option': 42}
    >>> dic = {'other_option': 42}
    >>> _extract_move_args(dic, 3)
    (False, 3, 3)
    """
    if do_pop:
        get = dic.pop
    else:
        get = dic.get
    res = [None]
    has_other = False

    for otherkey in ('move_limit', 'move_limit_each'):
        if otherkey in dic:
            val = get(otherkey)
            has_other = True
        else:
            val = get(otherkey, default)
        res.append(val)
    res[0] = get('move_children', has_other)
    return tuple(res)


if __name__ == '__main__':
    # added to ../mock.py as well:
    class MockBrain(object):
      def __repr__(self):
        return '<a brain>'
      def getObject(self):
        return MockObject()
    class MockObject(object):
      def __repr__(self):
        return '<an object>'
      def getHereAsBrain(self):
        return MockBrain()
    import doctest
    doctest.testmod()
