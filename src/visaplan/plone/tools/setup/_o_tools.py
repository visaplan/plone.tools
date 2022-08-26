# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Object tools for (_get_object).make_object_getter()
and (_make_folder).make_subfolder_creator()

All tools in this module are called in the same style.
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types
from six.moves import map

# Standard library:
from collections import defaultdict

# Zope:
from Products.CMFCore.utils import getToolByName

# Local imports:
from visaplan.plone.tools._have import HAS_SUBPORTALS, HAS_VPSEARCH
from visaplan.plone.tools.setup._args import (
    _extract_move_args,
    extract_layout_switch,
    extract_menu_switch,
    )
from visaplan.plone.tools.setup._exc import \
    AlreadyTranslated  # from LinguaPlone, or a dummy
from visaplan.plone.tools.setup._exc import \
    CantAddTranslationReference  # ... enhanced information

# Logging / Debugging:
from pdb import set_trace
from visaplan.tools.debug import pp

__all__ = [
        'handle_title',
        'handle_language',
        'handle_layout',
        'handle_menu',
        # minilogging system:
        'make_miniloggers',  # used here
        'make_notes_logger', # used in calling functions
        # operating on connected objects:
        ]

if HAS_SUBPORTALS:
    __all__.extend([
        'might_set_subportal',
        'handle_subportal',
        ])

if HAS_VPSEARCH:
    __all__.extend([
        'handle_united_search',
        ])
    # visaplan:
    from visaplan.plone.search.utils import (
        expand_localsearch,
        normalize_localsearch,
        storable_localsearch,
        )

# ----------------------------------------- [ minilogging system ... [
def make_notes_logger(logger, append_to=None):
    func = defaultdict(lambda: logger.error)
    func.update({
        'INFO': logger.info,
        'DEBUG': logger.debug,
        'ERROR': logger.error,
        })

    def logtup(tup):
        key, txt = tup
        func[key](txt)
        if append_to:
            append_to.append(tup)

    return logtup


# allows to write full information to a list
def make_miniloggers(notes, keys=None):
    """
    Make a few functions!
    """
    if not keys:
        keys = 'DEBUG INFO ERROR'.split()
    def makelogfunc(key):
        def func(txt, mapping=None):
            if mapping is not None:
                if (isinstance(mapping, dict)
                    and 'o' in mapping
                    and '%(o)r' not in txt
                    ):
                    txt = '(%(o)r) '+txt
                txt %= mapping
            notes.append((key, txt))
        func.__name__ = key.lower()
        return func

    return tuple(map(makelogfunc, keys))
# ----------------------------------------- ] ... minilogging system ]


def handle_title(o, kwdict, created, do_pop=True):
    """
    title -- a given (chosen) title
    default_title -- a calculated title (computed from an id)
    set_title -- set it?
    """
    changed = False
    notes = []
    _DBG, _NFO, _ERR = make_miniloggers(notes)

    pop = (kwdict.pop if do_pop
           else kwdict.get)

    title_given =   'title' in kwdict
    title =         pop('title', None)
    default_title = pop('default_title', None)
    if title:
        title = title.strip()
    if not title:
        title = default_title
    set_title =     pop('set_title', None)
    if created:
        found_title = 0
    else:
        found_title = o.Title()

    if set_title is None:
        if created:
            set_title = bool(title or default_title)
        else:
            set_title = not found_title and bool(title or default_title)

    if title:
        if title != found_title:
            if set_title and title:
                o.setTitle(title)
                _NFO('%(o)r: old title %(found_title)r --> new title %(title)r',
                      locals())
                changed = True
            elif title:
                _ERR('%(o)r: old title %(found_title)r mismatches %(title)r',
                     locals())
            elif set_title >= 2:
                if title is None:
                    _DBG('%(o)r: to remove the old title %(found_title)r, provide the empty string',
                         locals())
                else:
                    _NFO('%(o)r: resetting old title %(found_title)r to the empty string',
                         locals())
                    o.setTitle('')
            elif set_title:
                _DBG('%(o)r: to remove the old title %(found_title)r, '
                     "specify title='' and set_title=2", locals())
        else:
            _NFO('%(o)r: checked title (%(found_title)r)', locals())
    elif set_title >= 2 and title_given:
        _NFO('%(o)r: resetting old title %(found_title)r to the empty string',
             locals())
        o.setTitle('')
    elif set_title:
        _DBG('%(o)r: no title given', locals())
        if found_title:
            _DBG('%(o)r: to remove the old title %(found_title)r, '
                 "specify title='' and set_title=2", locals())
    return changed, notes


def handle_language(o, kwdict, created, do_pop=True):  # ----- [ h.l. ... [
    """
    Handle the language and canonical keyword arguments for the given object
    `o`.

    o -- the object
    kwdict -- the kwargs dictionary of the calling function (will be consumed)
    created -- a boolean to tell whether the given object has just been
               created, affecting a few defaults

    Return a 2-Tuple (changed, notes);
    `notes` is in turn a list of ('INFO', `text`) tuples.
    """
    changed = False
    notes = []
    _DBG, _NFO, _ERR = make_miniloggers(notes)
    pt = getattr(o, 'portal_type', None)
    if pt == 'Plone Site':
        _NFO("%(o)r: Won't handle_language for site root!" % locals())
        return changed, notes
    elif 0:
        pp(o, kwdict, pt)
        set_trace()

    pop = (kwdict.pop if do_pop
           else kwdict.get)

    language_given =  'language' in kwdict
    language =        pop('language', None)
    set_language =    pop('set_language', None)
    if language_given and not created:
        found_language = o.Language()
    else:
        found_language = 0

    canonical_given = 'canonical' in kwdict
    canonical =       pop('canonical', None)
    set_canonical =   pop('set_canonical', None)
    if canonical_given and not created:
        found_canonical = o.getCanonical()
    else:
        found_canonical = 0

    if language_given:
        if set_language is None:
            _DBG('set_language?')
            if created:
                set_language = bool(language)
                _DBG('%(set_language)r (freshly created'
                     ' with language=%(language)r', locals())
            elif language != found_language:
                set_language = True
                _DBG('%(set_language)r (old and new values different;'
                     '%(found_language)r --> %(language)r)', locals())
            else:
                set_language = False
                _DBG('%(set_language)r (found no reason;'
                     '%(found_language)r --> %(language)r,'
                     '%(found_canonical)r --> %(canonical)r)', locals())

        if set_language is None:
            set_language = language != found_language

    if canonical:
        if created:
            if not language:
                _ERR('canonical given %(canonical)r but no language %(language)r'
                     ' for a freshly created object!', locals())
                set_canonical = False
        else:
            if not language_given:
                _DBG('canonical given %(canonical)r but no language; '
                     'using %(found_language)r ...', locals())
                language = found_language

    # ----------------------- [ canonical, with language implied ... [
    if canonical_given:
        if set_canonical is None:
            _DBG('set_canonical?')
            if not canonical and not found_canonical:
                set_canonical = False
                _DBG('%(set_canonical)r (old and new values falsy;'
                     '%(found_canonical)r, %(canonical)r)', locals())
            elif canonical != found_canonical:
                _DBG('%(set_canonical)r (different values;'
                     '%(found_canonical)r --> %(canonical)r)', locals())
                can_path = '(unknown)'
                found_path = '(unknown)'
                try:
                    tup = canonical.getPhysicalPath()
                    can_path = '/'.join(tup)
                    tup = found_canonical.getPhysicalPath()
                    found_path = '/'.join(tup)
                    set_canonical = found_path != can_path
                except Exception as e:
                    _ERR('Error! (%(e)r)', locals())
                    raise
                finally:
                    _NFO('\n<new canonical>.getPath = %(can_path)r,'
                         '\n<old canonical>.getPath = %(found_path)r', locals())
                if not set_canonical:
                    _DBG('"different" objects but equal paths!')
                    set_trace()
            elif (found_canonical
                    and language_given
                    and language != found_language):
                set_canonical = True
                _DBG('%(set_canonical)r (language change;'
                     '%(found_language)r --> %(language)r, '
                     '%(found_canonical)r --> %(canonical)r)', locals())
            else:
                set_canonical = False
                _DBG('%(set_canonical)r (found no reason;'
                     '%(found_language)r --> %(language)r (%(set_language)r),'
                     '%(found_canonical)r --> %(canonical)r)', locals())

        if set_canonical and not language:
            _ERR('canonical given (%(canonical)r) but no language!'
                 ' (%(language)r)', locals())
            set_canonical = False

        if set_canonical:
            if found_canonical and not created:
                _NFO('Resetting language (was %(found_language)r, '
                     'canonical was %(found_canonical)r)', locals())
                o.setLanguage('')
                changed = True
            if language:
                _NFO('Setting language to %(language)r', locals())
                o.setLanguage(language)
                changed = True
            if canonical and canonical != o:
                _NFO('Setting canonical to %(canonical)r', locals())
                try:
                    o.addTranslationReference(canonical)
                except AlreadyTranslated as e:
                    _ERR('%(o)r is already translated!', locals())
                    _ERR(str(CantAddTranslationReference(o, canonical)), {})
                    if 0: pp({
                        'o': o, 'canonical': canonical,
                        'identical?': canonical is o,
                        })
                    set_trace()
                    nochmal = 0
                    if nochmal:
                        o.addTranslationReference(canonical)
                    else:
                        # https://www.python.org/dev/peps/pep-0344/#explicit-exception-chaining
                        # should work, shouldn't it?! (for me, it won't)
                        raise CantAddTranslationReference(o, canonical) # from e
                else:
                    changed = True
    # ----------------------- ] ... canonical, with language implied ]

    if changed or not set_language:
        return changed, notes

    if set_language:
        _NFO('%(o)r: Setting language to %(language)r', locals())
        try:
            o.setLanguage(language)
        except AttributeError as e:
            _ERR('handle_language(%(o)r): %(e)r', locals())
            pp(locals(), 'Nochmal, mit Debugger:',
            'Fehler tritt auf in LinguaPlone (.getTranslation --> isCanonical)')
            set_trace()
            o.setLanguage(language)
        else:
            changed = True
    return changed, notes  # ---------------------- ] ... handle_language ]


def handle_layout(o, kwdict, created, do_pop=True):  # --- [ h.layout ... [
    """
    handle the layout matters; return a 3-tuple (changed, notes, updates)
    """
    changed = False
    notes = []
    updates = {}
    _DBG, _NFO, _ERR = make_miniloggers(notes)

    layout, do_set, do_get = extract_layout_switch(kwdict, do_pop=do_pop)
    found_layout = None
    if do_set:
        if not layout:
            do_set = False
            _ERR("Won't set layout because of missing value (%(layout)r)",
                 locals())
        else:
            found_layout = o.getLayout()
            if found_layout == layout:
                _NFO('Checked layout=%(layout)r', locals())
            else:
                o.selectViewTemplate(templateId=layout)
                _NFO('set layout to %(layout)r (was %(found_layout)r)', locals())
                changed = True
    if do_get:
        if found_layout is None:
            found_layout = o.getLayout()
        if found_layout:
            _NFO('Found layout to be %(found_layout)r', locals())
            updates['layout'] = found_layout
    return (changed, notes, updates)  # ----------- ] ... handle_language ]


def handle_menu(o, kwdict, created, do_pop=True):  # -- [ handle_menu ... [
    """
    Handle the language and canonical keyword arguments for the given object
    `o`.

    o -- the object
    kwdict -- the kwargs dictionary of the calling function (will be consumed)
    created -- a boolean to tell whether the given object has just been
               created, affecting a few defaults

    Return a 2-Tuple (changed, notes);
    `notes` is in turn a list of ('INFO', `text`) tuples.
    """
    changed = False
    notes = []
    _DBG, _NFO, _ERR = make_miniloggers(notes)

    switch_menu = extract_menu_switch(kwdict, created, do_pop=do_pop)
    if switch_menu is not None:
        val = not switch_menu
        try:
            set_to = o.setExcludeFromNav
        except AttributeError:
            pt = getattr(o, 'portal_type', None)
            if pt == 'Plone Site':
                # this is expected:
                _NFO('%(o)r (%(pt)r) has no setExcludeFromNav attribute'
                     % locals())
            else:
                _ERR('%(o)r (%(pt)r) has no setExcludeFromNav attribute!'
                     % locals())
        else:
            set_to(val)
            _NFO('%(o)r: setExcludeFromNav(%(val)r)', locals())
            changed = True
    else:
        _DBG('switch_menu is %(switch_menu)r', locals())

    return changed, notes  # -------------------------- ] ... handle_menu ]


# --------------------------------- [ depends on visaplan.plone.subportals ... [
def might_set_subportal(kwdict):
    """
    The given keyword arguments indicate that a subportal *might* be set.

    I might not, even if this function returns True, because:

    - the subportal is already added
    - the `set_subportal` key is callable and might return False

    The kwdict dictionary is not consumed.

    >>> dic1 = {'only_other_keys': 42}
    >>> might_set_subportal(dic1)
    False
    >>> dic1
    {'only_other_keys': 42}
    >>> dic2 = {'subportal': 'some-subportal-id'}
    >>> might_set_subportal(dic2)
    True

    If `set_subportal` is callable, it *might* return True,
    but we don't try it (we don't have an object):
    >>> dic3 = {'subportal': 'other-subportal-id',
    ...         'set_subportal': lambda: False}
    >>> might_set_subportal(dic3)
    True

    However, if no subportal is available, it can't be set:
    >>> dic4 = {'set_subportal': True}
    >>> might_set_subportal(dic4)
    False
    """
    get = kwdict.get
    subportal = get('subportal')
    set_subportal = get('set_subportal')
    if set_subportal is None:
        return bool(subportal)
    elif (not set_subportal  # False
           or not subportal):
        return False
    else:
        return True


def handle_subportal(o, kwdict, created, do_pop=True):
    """
    Unitracc-specific functionality (visaplan.plone.subportals)
    """
    changed = False
    notes = []
    _DBG, _NFO, _ERR = make_miniloggers(notes)

    pop = (kwdict.pop if do_pop
           else kwdict.get)
    subportal_given = 'subportal' in kwdict
    set_subportal = pop('set_subportal', None)
    if callable(set_subportal):
        set_subportal, subportals = set_subportal(o)
    else:
        subportal = pop('subportal')
        if set_subportal is None:
            set_subportal = bool(subportal)
        elif not subportal and set_subportal:
            _NFO("Won't set_subportal %(subportal)r", locals())
            set_subportal = False
        if set_subportal:
            found_subportals = o.getSubPortals()
            found_set = set(found_subportals)
            if isinstance(subportal, six_string_types):
                wanted_set = set([subportal])
            else:
                wanted_set = set(subportal)
            _DBG('%(o)r: registered for subportals %(found_subportals)r', locals())

            added_set = wanted_set - found_set
            if added_set:
                subportals = list(found_subportals) + list(added_set)
            else:
                _NFO('%(o)r: checked subportal %(subportal)r', locals())
                set_subportal = False

    if set_subportal:
        o.setSubPortals(subportals)
        return True, notes
    return False, notes
# --------------------------------- ] ... depends on visaplan.plone.subportals ]


# ------------------------------------- [ depends on visaplan.plone.search ... [
def handle_united_search(siblings, opt, src_lang):
    """
    Unitracc-specific functionality (visaplan.plone.search):

    Take a given local search configuration from the primary object
    (siblings[src_lang]) and modify it to contain the paths of the siblings as
    well; this configuration is then applied to all siblings.

    Any changes are done to the @@settings in the pickle storage
    and don't affect the catalog brains.
    """
    if src_lang is not None:
        otherval = opt.get('src_lang' )
        if otherval is not None:
            assert src_lang == otherval
    else:
        src_lang = opt['src_lang']
    logger = opt['logger']
    me = 'handle_united_search'
    if src_lang is None:
        logger.warn('%(me)s: no source language for %(siblings)s', locals())
        return 0
    siblings = siblings.copy()  # a simple copy should be sufficient
    src_o = siblings.pop(src_lang)
    # get complete configuration:
    settings = opt['portal'].getBrowser('unitraccsettings')
    localsearch_all = settings.get('localsearch', {})

    src_uid = src_o.UID()
    src_search_raw = localsearch_all.get(src_uid)
    if not src_search_raw:
        logger.warn('%(me)s: no localsearch settings'
                    ' for %(src_o)r (%(src_uid)s)', locals())
        return 0
    src_search = normalize_localsearch(src_o, src_search_raw)
    logger.info('%(me)s: localsearch for UID %(src_uid)r: %(src_search)r', locals())
    pp(('src_o:', src_o), ('src_uid:', src_uid), ('search (stored):', src_search_raw), ('search (normalized):', src_search))
    search_path = src_search_raw.get('path')  # '.' oder SPEC oder so

    NOPATH = src_search.get('path') == 'NOPATH'
    if NOPATH:
        logger.info("%(me)s: localsearch for %(src_o)r"
                    " doesn't contain a path restriction"
                    ' (%(src_search_raw)s)', locals())
        added_here = frozenset()

    src_search_exp = expand_localsearch(src_o, src_search)
    src_paths = set(src_search_exp['path'])  # full path specs
    updated_settings = {}
    src_changes = False

    for la, other_o in siblings.items():
        other_uid = other_o.UID()
        logger.info('%(me)s: UID %(other_uid)r --> %(other_o)r', locals())
        if other_uid == src_uid:
            logger.info('%(me)s: UID equals source UID %(src_uid)r', locals())
            continue

        other_search_raw = localsearch_all.get(other_uid)
        if not other_search_raw:
            logger.info('%(me)s: No localsearch for UID %(other_uid)r so far', locals())
            if not NOPATH:
                tup = other_o.getPhysicalPath()
                other_path = '/'.join(tup)
                added_here = set([other_path])
        else:
            other_search = normalize_localsearch(other_o, other_search_raw)
            updated_settings[other_uid] = other_search
            other_search_exp = expand_localsearch(other_o, other_search)
            other_paths = set(other_search_exp['path'])
            logger.info('%(me)s: localsearch for UID %(other_uid)r: %(other_search)r', locals())
            if other_search['path'] == 'NOPATH':
                if NOPATH:
                    logger.info('%(me)s: localsearch for %(other_uid)r specifies NOPATH.', locals())
                else:
                    logger.warn('%(me)s: localsearch for %(other_uid)r specifies NOPATH.'
                                ' This will be changed!', locals())
            else:
                txt = ', '.join(sorted(other_paths))
                logger.info('%(me)s: localsearch for %(other_uid)r specifies %(txt)s', locals())
                if NOPATH:
                    logger.warn('%(me)s: path restriction for %(other_uid)r will be removed!', locals())
                else:
                    missing_here = src_paths - other_paths
                    if missing_here:
                        txt = ', '.join(sorted(missing_here))
                        # will be done below:
                        logger.info('%(me)s: localsearch for %(other_uid)r: adding %(txt)s', locals())

                    added_here = other_paths - src_paths
                    if added_here:
                        txt = ', '.join(sorted(missing_here))
                        logger.info('%(me)s: localsearch for %(other_uid)r: found %(txt)s', locals())
                        src_paths.update(added_here)
                        src_changes += 1

    if src_changes:
        src_search['path'] = sorted(src_paths)
        stored_dict = storable_localsearch(src_o, src_search)
        logger.info('%(me)s: Changing localsearch for %(src_uid)r to %(stored_dict)s', locals())

    for la, other_o in siblings.items():
        other_uid = other_o.UID()
        updated_settings.setdefault(other_uid, src_search)
        other_search = updated_settings[other_uid]
        paths_here = set(other_search['path'])
        paths_here.update(src_paths)
        other_search['path'] = sorted(paths_here)
        stored_dict = storable_localsearch(other_o, other_search)
        logger.info('%(me)s: Setting localsearch for %(other_uid)r to %(stored_dict)s', locals())
# ------------------------------------- ] ... depends on visaplan.plone.search ]
