# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Helpers for arguments exploitation
"""

# Python compatibility:
from __future__ import absolute_import, print_function

try:
    # visaplan:
    from visaplan.tools.minifuncs import check_kwargs
except ImportError as e:
    if __name__ == '__main__':
        def dummy(*args, **kwargs):
            pass
        check_kwargs = dummy
        print('W: %(e)r Some tests might fail' % locals())
    else:
        raise

__all__ = [
        # Helferlein für **kwargs:
        'extract_object_and_brain', # --> (o, brain)
        'extract_object_or_brain',  # --> (o, brain=None)
        'extract_brain_or_object',  # --> (brain, o=None)
        # [switch_]menu:
        'extract_menu_switch',
        'normalize_menu_switch',
        'extract_layout_switch',
        # query manipulation:
        'apply_move_order_options',
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


def extract_menu_switch(dic, created, default=None, do_pop=True):
    """
    Extract the switch_menu and/or menu (boolean) value
    from the given dict; if both are present but different,
    a ValueError is raised.

    Other than normalize_menu_switch (below), this function takes other
    keys into account as well, e.g. "created".

    We'll use a little test helper which enforces the `created` argument to be
    given by name, for enhanced clarity:
    >>> def ems(dic, **kwargs):
    ...     return extract_menu_switch(dic, **kwargs)

    >>> dic={'switch_menu': 1, 'menu': 1, 'other': 42}
    >>> sorted(dic.items())
    [('menu', 1), ('other', 42), ('switch_menu', 1)]
    >>> ems(dic, created=None, do_pop=False)
    1

    With do_pop=False, the dictionary is not changed:
    >>> sorted(dic.items())
    [('menu', 1), ('other', 42), ('switch_menu', 1)]

    The default is, however, to remove the used options:
    >>> ems(dic, created=None)
    1
    >>> dic
    {'other': 42}

    1 and True are equivalent:
    >>> dic2={'switch_menu': 1, 'menu': True, 'other': 43}
    >>> extract_menu_switch(dic2, created=None)
    1
    >>> dic2
    {'other': 43}

    If both menu and switch_menu are given but different, we'll get an error:
    >>> ems({'switch_menu': 1, 'menu': 0}, created=None)
    Traceback (most recent call last):
    ...
    ValueError: 'menu': 0 conflicts 'switch_menu' value 1!

    With created=True, the default is to *not* activate the menu entry:
    >>> ems({}, created=True)
    False

    With set_menu=False, None will be returned:
    >>> ems({'switch_menu': 1, 'menu': True, 'set_menu': False}, created=None)

    Without a 'set_menu' value, the default depends on the `created` argument.
    For freshly created items, the default is "no change":
    >>> ems({'switch_menu': 1}, created=True)

    >>> ems({'switch_menu': 1}, created=False)
    1

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
    set_menu = get('set_menu', None)
    if set_menu is None:
        if created:
            if res is None:
                return False
            else:
                return None
        return res
    elif not set_menu:
        return None
    elif res is None:
        return default
    else:
        return res


def normalize_menu_switch(dic):
    """
    Return the value of the first menu-switching option,
    check for conflicts, and remove superfluous (but not conflicting)
    keys.

    >>> dic1={'switch_menu': 1, 'menu': 1, 'other': 42}
    >>> normalize_menu_switch(dic1)
    1
    >>> sorted(dic1.items())
    [('other', 42), ('switch_menu', 1)]

    The keys are not added if missing:
    >>> dic2={'other': 43}
    >>> normalize_menu_switch(dic2)
    >>> sorted(dic2.items())
    [('other', 43)]

    Conflicting specifications cause an error:
    >>> dic3={'switch_menu': 1, 'menu': 0}
    >>> normalize_menu_switch(dic3)
    Traceback (most recent call last):
      ...
    ValueError: 'menu': 0 conflicts 'switch_menu' value 1!

    The function is sometimes used just to normalize the given dict,
    ignoring the return value:

    >>> dic1={'switch_menu': 1, 'menu': 1, 'other': 42}
    >>> def f(dic):
    ...     normalize_menu_switch(dic)
    ...     return sorted(dic.items())
    >>> f(dic1)
    [('other', 42), ('switch_menu', 1)]

    The keys are not added if missing:
    >>> f({'other': 43})
    [('other', 43)]

    """
    get = dic.get
    res = None
    keys = []
    allowed = (
        'switch_menu',
        'menu',
        )
    first = True
    firstval = None
    for key in allowed:
        if first:
            val = dic.get(key, None)
            firstval = val
            first = False
        else:
            val = dic.pop(key, None)
        if val is not None:
            if res is None:
                res = val
            elif val != res:
                earlier = keys[1:] and tuple(keys) or keys[0]
                raise ValueError('%(key)r: %(val)r conflicts '
                                 '%(earlier)r value %(res)r!'
                                 % locals())
            keys.append(key)
    if res is not None and firstval is None:
        dic[allowed[0]] = res
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


def setdefault_move_args(dic, default=None):
    """
    Like _extract_move_args (above), but never pops keys from the dict
    but rather amends the missing keys (since we seem to work recursively now
    and re-use the kwargs dictionaries down the trip).

    Since the {}.setdefault method returns the value set, and for testability,
    it returns the same 3-tuple like _extract_move_args.

    >>> dic = {'move_limit': 1, 'other_option': 42}
    >>> setdefault_move_args(dic)
    (True, 1, None)

    >>> def si(dic): return sorted(dic.items())
    >>> si(dic)
    [('move_children', True), ('move_limit', 1), ('move_limit_each', None), ('other_option', 42)]
    >>> dic = {'other_option': 42}
    >>> setdefault_move_args(dic, 3)
    (False, 3, 3)
    >>> si(dic)
    [('move_children', False), ('move_limit', 3), ('move_limit_each', 3), ('other_option', 42)]
    """
    res = [None]
    has_other = False
    get = dic.get

    for otherkey in ('move_limit', 'move_limit_each'):
        if otherkey in dic:
            val = get(otherkey)
            has_other = True
        else:
            dic[otherkey] = default
            val = default
        res.append(val)
    res[0] = dic.setdefault('move_children', has_other)
    return tuple(res)


def setdefault_source_language(dic, default=None):
    """
    This function modifies the given dict in-place;
    like the {}.setdefault method, it returns the actual value.

    Besides the verbose 'source_language' key, the 'src_lang' alias
    is considered as well. If both are found, they must be equal.

    >>> dic={'src_lang': 'de'}
    >>> setdefault_source_language(dic, None)
    'de'
    >>> dic
    {'source_language': 'de'}
    >>> dic={'src_lang': 'de', 'source_language': 'en'}
    >>> setdefault_source_language(dic, None)
    Traceback (most recent call last):
    ...
    ValueError: Conflicting values for source_language ('en') and src_lang ('de')!
    """
    res = []
    has_other = False
    first = True

    for otherkey in ('source_language', 'src_lang'):
        if first:
            get = dic.get
            first = False
        else:
            get = dic.pop
        if otherkey in dic:
            res.append(get(otherkey))
    if len(set(res)) == 1:
        dic['source_language'] = res[0]
        return res[0]
    elif not res:
        dic['source_language'] = default
        return default
    else:
        raise ValueError('Conflicting values for source_language (%r)'
                ' and src_lang (%r)!' % tuple(res))


def apply_move_order_options(query, kwargs, **kw):
    """
    This function modifies the given `query` in-place, by default
    (`do_pop`=True) consuming the given kwargs dictionary.

    Since we build a query for move operations, we like to maintain a given
    position in the source folder.

    We'll use two little test helpers here:

    >>> def amoo(query, **kwargs):  # finalizing (default)
    ...     apply_move_order_options(query, kwargs)
    ...     return sorted(query.items())
    >>> def amoo_nf(query, **kwargs):  # non-finalizing
    ...     apply_move_order_options(query, kwargs, finalize=False)
    ...     return sorted(query.items())

    If a depth of 1 is specified, the default order is by position in parent:
    >>> amoo_nf({'path': '/Plone/some/path', 'depth': 1})
    [('depth', 1), ('path', '/Plone/some/path'), ('sort_on', 'getObjPositionInParent')]
    >>> amoo_nf({'path': '/Plone/some/path'}, depth=1)
    [('depth', 1), ('path', '/Plone/some/path'), ('sort_on', 'getObjPositionInParent')]

    The default ordering by position in parent is fine for moving contents from
    a single source folder to a single destination; but if you are collecting
    objects from several folders, most likely this would either yield
    unpredictable results, or you'd reflect the order of the parents processed
    in the result.  In such cases, you'll want to sort by some more reasonable
    value, e.g. by some date. The default date index used is 'created':

    >>> q2 = {'path': '/Plone/some/path'}
    >>> amoo_nf(q2)
    [('path', '/Plone/some/path'), ('sort_on', 'created')]

    ... but you can specify another date which is is used unless a depth of 1
    is given (or some other sorting specification is already present):

    >>> q3 = {'path': '/Plone/some/path'}
    >>> amoo_nf(q3, use_date='effective')
    [('path', '/Plone/some/path'), ('sort_on', 'effective')]

    >>> q4 = {'path': '/Plone/some/path', 'depth': 1}
    >>> amoo_nf(q4, use_date='effective')
    [('depth', 1), ('path', '/Plone/some/path'), ('sort_on', 'getObjPositionInParent')]

    So far, we have suppressed finalization, because this yields simpler
    results.
    To make sure you get a usable query dict, specify `finalize=True`:
    >>> amoo(q4)
    [('path', {'operator': 'or', 'query': ['/Plone/some/path'], 'depth': 1}), ('sort_on', 'getObjPositionInParent')]

    >>> q5 = {'path': '/Plone/some/path'}
    >>> amoo_nf(q5, sort_on='effective')
    [('path', '/Plone/some/path'), ('sort_on', 'effective')]
    >>> amoo(q5)
    [('path', {'operator': 'or', 'query': ['/Plone/some/path']}), ('sort_on', 'effective')]

    We can do this in one step as well, of course:

    >>> q6 = {'path': '/Plone/some/path'}
    >>> amoo(q6, sort_on='effective')
    [('path', {'operator': 'or', 'query': ['/Plone/some/path']}), ('sort_on', 'effective')]

    The depth specification is supposed to live in the `path` specification.
    With finalize=True, this will be rectified.

    Finally, here are the supported keyword-only options:

    `finalize` (default: True), create a *valid* `path` filter (if given)
    `do_pop` (default: True), pop the keys from the "kwargs" which contain the
             defaults
    `strict` (default: True), raise an error if undefined keyword arguments are
             specified (see the `check_kwargs` function)

    """
    do_pop = kw.pop('do_pop', True)
    finalize = kw.pop('finalize', True)
    check_kwargs(kw)
    if do_pop:
        get = kwargs.pop
    else:
        get = kwargs.get

    path_given = 'path' in query
    depth_given = 'depth' in query
    depth_root = query.get('depth')
    depth = None
    if path_given:
        path = query.get('path')
        if isinstance(path, dict):
            depth = path.get('query')
            if (depth      is not None and
                depth_root is not None and
                depth != depth_root):
                raise ValueError('conflicting depth specs! '
                                 ' (depth=%(depth_root)r, '
                                  ' path=%(path)s)'
                                  % locals())
    if (depth      is     None and
        depth_root is not None):
        depth = depth_root
    if depth is None:
        depth = get('depth', None)
    if depth is not None:
        query['depth'] = depth
    if 'sort_on' not in query:
        if 'sort_on' in kwargs:
            sort_on = get('sort_on')
            if sort_on:
                query['sort_on'] = sort_on
        elif depth == 1:
            query['sort_on'] = 'getObjPositionInParent'
        elif depth != 0:
            use_date = get('use_date', None) or 'created'
            query['sort_on'] = use_date
    if finalize:
        if 'path' in query:
            path = query['path']
            if isinstance(path, dict):
                path_dict = path
            elif isinstance(path, list):
                path_dict = {
                    'query': path,
                    'operator': 'or',
                    }
            elif isinstance(path, tuple):
                path_dict = {
                    'query': list(path),
                    'operator': 'or',
                    }
            else:
                path_dict = {
                    'query': path.split(),
                    'operator': 'or',
                    }
            if 'depth' in query:
                del query['depth']
            if depth is not None:
                path_dict['depth'] = depth
            query['path'] = path_dict


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
    # Standard library:
    import doctest
    doctest.testmod()
