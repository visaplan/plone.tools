# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
Object tools for (_get_object).make_object_getter()
and (_make_folder).make_subfolder_creator()

All tools in this module are called in the same style.
"""

# Python compatibility:
from __future__ import absolute_import

from six.moves import map

# Standard library:
from collections import defaultdict
from pprint import pprint

# Zope:
from Products.CMFCore.utils import getToolByName

# Local imports:
from ._args import (
    _extract_move_args,
    extract_layout_switch,
    extract_menu_switch,
    )
from ._exc import AlreadyTranslated  # from LinguaPlone, or a dummy
from ._exc import CantAddTranslationReference  # ... enhanced information

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


def handle_language(o, kwdict, created, do_pop=True):
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
                    if 0: pprint({
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

    if changed:  # if canonical was given, we'll have set the language
        return changed, notes

    if set_language:
        _NFO('Setting language to %(language)r', locals())
        o.setLanguage(language)
        changed = True
    return changed, notes


def handle_layout(o, kwdict, created, do_pop=True):
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
    return (changed, notes, updates)


def handle_menu(o, kwdict, created, do_pop=True):
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
        o.setExcludeFromNav(val)
        _NFO('%(o)r: setExcludeFromNav(%(val)r)', locals())
        changed = True
    else:
        _DBG('switch_menu is %(switch_menu)r', locals())

    return changed, notes
