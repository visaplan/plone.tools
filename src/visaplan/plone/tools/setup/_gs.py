# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
"""
visaplan.plone.tools:setup._gs (GenericSetup usage)
"""

# Python compatibility:
from __future__ import absolute_import

from six import string_types as six_string_types

try:
    # Zope:
    from Products.CMFCore.utils import getToolByName

    # Plone:
    from plone.app.upgrade.utils import loadMigrationProfile
except ImportError:
    if __name__ != '__main__':  # for doctests
        raise


# visaplan:
from visaplan.tools.lands0 import make_default_prefixer

safe_context_id = make_default_prefixer('profile-',
                                        ['snapshot-'])


def extract_profile_name(kwargs):
    """
    Extract the profile argument from the given kwargs dict

    A little helper for the load_and_cook function:
    We require a profile argument for load_and_cook!

    We require a `profile` argument, and we'll use a `suffix` argument if
    given.

    First, a little test helper:
    >>> def epn(kw):
    ...     res = extract_profile_name(kw)
    ...     return res, kw
    >>> kw = {'profile': 'my.fancy.product:nondefault',
    ...       'tuples': [('cssregistry', 'portal_css')]}
    >>> epn(kw)                                # doctest: +NORMALIZE_WHITESPACE
    ('profile-my.fancy.product:nondefault',
     {'tuples': [('cssregistry', 'portal_css')]})

    Given a naked product name, a ':default' suffix is appended:
    >>> kw = {'profile': 'my.fancy.product'}
    >>> epn(kw)
    ('profile-my.fancy.product:default', {})
    >>> kw = {'profile': 'my.fancy.product', 'suffix': 'other'}
    >>> epn(kw)
    ('profile-my.fancy.product:other', {})

    An explicitly given suffix will override a suffix given in the profile
    argument:
    >>> kw = {'profile': 'my.fancy.product:default',
    ...       'suffix':  'another'}
    >>> epn(kw)
    ('profile-my.fancy.product:another', {})
    >>> kw = {'profile': 'snapshot-my.fancy.product:default',
    ...       'suffix':  'another'}
    >>> epn(kw)
    ('snapshot-my.fancy.product:another', {})

    """
    pop = kwargs.pop
    profile = pop('profile')
    profile = safe_context_id(profile)
    stem, sep, suff = profile.partition(':')
    suffix = pop('suffix', None)
    if suff:
        if suffix is not None:
            profile = stem + ':' + suffix
    else:
        if suffix is None:
            suffix = 'default'
        profile = stem + ':' + suffix
    return profile


def load_and_cook(context, logger, **kwargs):
    """
    Universal loader and cooker

    By default, we load and cook the Javascript and CSS resources (see the
    `tuples` option)
    of the given profile (profile, suffix options);

    but often we need to recompile (cook) those resources after processing
    foreign profile: This is what the `after_profiles` option is for.
    Here we currently expect complete specifications, including 'profile-' pre-
    and ':default' suffixes.
    """
    info = logger.info
    pop = kwargs.pop
    after_profiles = pop('after_profiles', None)
    if after_profiles is not None:
        if isinstance(after_profiles, six_string_types):
            after_profiles = after_profiles.split()
        for profile in after_profiles:
            info('Profile %(profile)r ...', locals())
            loadMigrationProfile(context, profile)

    tuples = pop('tuples', None)
    if tuples is None:
        tuples = [
            ('jsregistry',  'portal_javascripts'),
            ('cssregistry', 'portal_css'),
            ]

    profile = extract_profile_name(kwargs)
    setup = getToolByName(context, 'portal_setup')
    run_step = setup.runImportStepFromProfile
    for xmlname, toolname in tuples:
        info('Profile %(profile)r: %(xmlname)s[.xml]', locals())
        try:
            run_step(profile, xmlname)
        except Exception as e:
            logger.error('error running %(xmlname)r[.xml] from %(profile)s',
                         locals())
            logger.error('Exception: %(e)r', locals())
            logger.error('e.args: %s', (e.args,))
            raise

        tool = getToolByName(context, toolname)
        info('toolname %(toolname)r --> tool %(tool)r', locals())
        try:
            tool.cookResources()
        except AttributeError as e:
            logger.error('%(xmlname)s[.xml]: '
                         'The %(toolname)r tool lacks a cookResources method'
                         ' %(tool)r',
                         locals())
            raise
        else:
            info('%(xmlname)s resources cooked.', locals())


if __name__ == '__main__':
    # Standard library:
    import doctest
    doctest.testmod()
