# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Kontext-Helferlein:

Funktionen, die im Rahmen eines Aufruf-Kontexts hilfreich sind
(also nicht über den aktuellen Request hinaus)
"""

# Python compatibility:
from __future__ import absolute_import, print_function

from six import string_types as six_string_types

# Setup tools:
import pkg_resources

# Standard library:
from traceback import extract_stack

# Zope:
from Products.CMFCore.utils import getToolByName

# Plone:
from Products.CMFPlone import PloneMessageFactory as pmf

# visaplan:
from visaplan.tools.coding import safe_decode
from visaplan.tools.minifuncs import check_kwargs, gimme_False

# Logging / Debugging:
import logging
from visaplan.plone.tools.log import getLogSupport
from visaplan.tools.debug import asciibox, log_or_trace

try:
    pkg_resources.get_distribution('zope.i18n')
except pkg_resources.DistributionNotFound:
    HAS_ZOPE_I18N = False
else:
    HAS_ZOPE_I18N = True
    # Zope:
    from zope.i18n import translate as z3translate

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           5,   # getMessenger; make_permissionChecker improved
           )

__all__ = ['getActiveLanguage',
           'getSupportedLanguageTuples',
           'make_translator',
           'make_pathByUIDGetter',
           'make_permissionChecker',
           'make_timeFormatter',
           'make_userdetector',
           'make_SessionDataProxy',
           'message',       # uses safe_decode
           'getMessenger',  # accepts a decoder argument
           'getbrain',
           'make_brainGetter',
           'parents',
           'parent_brains',
           'get_parent',
           'getPath',
           'get_published_templateid',
           ]


def getActiveLanguage(context):
    """
    Gib den Code der aktiven Sprache zurück;
    wie der Adapter langcode (aus tomcom.adapter), aber "sicherer"
    """
    language_tool = getToolByName(context, 'portal_languages')
    codes = language_tool.getSupportedLanguages()
    request = context.REQUEST
    la = request.get('LANGUAGE')
    if la and la in codes:
        return la
    return language_tool.getDefaultLanguage()


def getSupportedLanguageTuples(context):
    """
    Return a list of language tuples, for the languages supported in this site
    """
    language_tool = getToolByName(context, 'portal_languages')
    getName = language_tool.getNameForLanguageCode
    liz = []
    for langCode in language_tool.getSupportedLanguages():
        liz.append((langCode, getName(langCode)))
    return liz


def make_translator(context, domain=None, target_language=None):
    """
    Create a function which calls zope.i18n.translate with sensible defaults
    """
    if not HAS_ZOPE_I18N:
        def dummy(msgid,
                  domain=domain,
                  mapping=None,
                  target_language=target_language,
                  default=None):
            """
            translation dummy; zope.i18n not installed
            """
            return default or msgid
        return dummy

    if not domain:
        domain = 'plone'
    if not target_language:
        target_language = getActiveLanguage(context)
    def translate(msgid,
                  domain=domain,
                  mapping=None,
                  target_language=target_language,
                  default=None):
        if not domain:
            domain = 'plone'
        if not target_language:
            target_language = getActiveLanguage(context)
        return z3translate(msgid, domain, mapping,
                           context, target_language, default)
    return translate


def make_permissionChecker(context=None, getAdapter=None,
                           checkperm=None, verbose=None):
    """
    Create a function to check the given permission.

    Options:

    context -- usually the only one given.
               If so, the usual membership_tool.checkPermission method is used,
               with a context default value injected.

    Please specify all following options by name:

    getAdapter -- deprecated;
                  if given, it is used to get a 'checkperm' adapter
                  (which is not present in standard Plone and uses a fixed
                  context argument, which is the one bound to that getAdapter
                  method)
    checkperm -- rarely needed: You might want to use a special permission
                 checking function and add the logging facility.
    verbose -- if True, every check for a permission will be logged.

    Usage:

      checkperm = make_permissionChecker(context)
      if not checkperm('Manage portal'):
          raise Unauthorized
    """
    if checkperm is None:
        if getAdapter is not None:
            try:  # traditional / deprecated usage:
                checkperm = getAdapter('checkperm')
            except:
                pass
    if checkperm is None:
        if context is None:
            raise ValueError('At least the context is needed!')
        membership_tool = getToolByName(context, 'portal_membership')
        _cp = membership_tool.checkPermission
        def checkperm(permission, context=context):
            return _cp(permission, context)

    if verbose:
        # bisher nur mit Modul-, nicht mit Funktions-/Methodeninformation:
        logger = getLogSupport(stack_limit=4)[0]
        log = logger.info
        def cp_verbose(permission):
            val = checkperm(permission)
            log('checkperm(%(permission)r) --> %(val)r', locals())
            return val
        return cp_verbose
    return checkperm


def make_timeFormatter(context, longFormat=False):
    """
    Wie der Adapter totime
    """
    util = getToolByName(context, 'translation_service')
    func = util.ulocalized_time
    request = context.REQUEST

    def format(time, longFormat=longFormat):
        return func(time, longFormat,
                    context=context,
                    domain='plonelocales',
                    request=request)
    return format


def make_SessionDataProxy(context):
    """
    Stellt die Sitzung als Dict. zur Verfügung;
    für fehlende Schlüssel wird None zurückgegeben.
    """

    session = context.REQUEST.SESSION

    class SDProxy(dict):
        """
        session: in Closure
        """
        def __getitem__(self, key):
            try:
                return dict.__getitem__(self, key)
            except KeyError:
                if session.has_key(key):
                    val = session.get(key)
                    dict.__setitem__(self, key, val)
                else:
                    val = None
                    session.set(key, val)
                return val

        def __setitem__(self, key, val):
            dict.__setitem__(self, key, val)
            session.set(key, val)

        def __delitem__(self, key):
            try:
                del session[key]
            except KeyError:
                pass
            try:
                del self[key]
            except KeyError:
                pass

    return SDProxy()


class SessionDataProxy(dict):
    """
    Stellt die Sitzung als Dict. zur Verfügung;
    für fehlende Schlüssel wird None zurückgegeben.
    """
    def __init__(self, context):
        # sdm = getToolByName(context, 'session_data_manager')
        # self.session = sdm.getSessionData(create=True)
        self.session = context.REQUEST.SESSION

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            val = self.session.get(key)
            dict.__setitem__(self, key, val)
            return val

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)
        self.session[key] = val

    def __delitem__(self, key):
        try:
            del self.session[key]
        except KeyError:
            pass
        try:
            del self[key]
        except KeyError:
            pass


def make_userdetector(ids, splitter=None, getid=True, verbose=None):
    """
    Gib eine Funktion zurück, die True zurückgibt, wenn ein Benutzer mit einer
    der angegebenen IDs angemeldet ist, und ansonsten False.
    Wenn die Liste leer ist, wird eine Funktion zurückgegeben, die ohne
    weiteres Federlesens False zurückgibt.

    ids -- die Benutzer-IDs
    splitter -- wenn ids ein String ist, übergeben an die split-Methode;
                None (Vorgabe): jeder Leerraum
    getid -- wenn True (Vorgabe), wird die Benutzer-ID oder None zurückgegeben,
             sonst True oder False
    verbose -- wenn True, wird beim Erzeugen des Detektors eine Zeile nach
               StdOut geschrieben. Vorgabe ist True, wenn <splitter> einen
               möglicherweise sinnlosen Wert hat, sonst False.

    Verwendung:

    >>> watched_user = make_userdetector('heinz willy')
    >>> if watched_user(context=context):
    >>>     # angemeldeter Benutzer ist 'heinz' oder 'willy'
    >>>     ...
    """
    if not ids:
        return gimme_False
    elif isinstance(ids, six_string_types):
        ids = ids.split(splitter)
        if not ids:
            return gimme_False
    IDS = frozenset(ids)
    if verbose is None:
        verbose = (splitter is not None
                   and len(splitter) > 1
                   )
    if verbose:
        print('*' * 79)
        print('make_userdetector(%s)' % arginfo(sorted(IDS), getid=getid))
        print('*' * 79)

    def get_userid(**kwargs):
        x = kwargs.get('member_id', None)
        if x:
            return x
        x = kwargs.get('member', None)
        if x:
            return x.getId()
        auth = kwargs.get('auth')
        if auth is None:
            getAdapter = kwargs.get('getAdapter')
            if getAdapter is not None:  # olde / depretated usage:
                try:
                    auth = getAdapter('auth')
                except:
                    pass
            if auth is None:
                context = kwargs.get('context')
                if context is None:
                    raise ValueError('Please specify the context!')
                membership_tool = getToolByName(context, 'portal_membership')
                auth = membership_tool.getAuthenticatedMember
        member = auth()
        return member.getId()

    def get_watched_userid(**kwargs):
        usid = get_userid(**kwargs)
        if usid and usid in IDS:
            return usid
        return None

    def user_is_one_of(**kwargs):
        usid = get_userid(**kwargs)
        if usid and usid in IDS:
            return True
        return False

    if getid:
        return get_watched_userid
    else:
        return user_is_one_of


def decorated_tool(context, toolname, limit_get_delta=0, limit=3):
    """
    Gib eine "dekorierte" Fassung des übergebenen Tools zurück

    Argumente:

    -- context, toolname -- weitergereicht an getToolByName
    -- limit_get_delta -- eine Ganzzahl, die das limit-Argument für
                    extract_stack für die *Beschaffung* des Tools gegenüber
                    seiner *Verwendung* erhöht.
                    Bei Aufruf durch einen Adapter ist 1 zu übergeben.
    -- limit -- weitergereicht an extract_stack
    """
    logger = logging.getLogger('decorated_tool %(toolname)r' % locals())
    def caller_info(limit=limit):
        raw_info = extract_stack(limit=limit)
        filename, lineno, funcname = raw_info[0][:3]
        if filename.endswith('.pyc'):
            filename = filename[:-1]
        if funcname:
            prefix = '%(filename)s[%(funcname)s]: %(lineno)d'
        else:
            prefix = '%(filename)s: %(lineno)d'
        return prefix % locals()

    ci = caller_info(limit+limit_get_delta)
    logger.info('GET:  ' + ci)
    print('*** ' + ci)
    print('*** getting tool %(toolname)r' % locals())

    tool = getToolByName(context, toolname)
    def decorated(*args, **kwargs):
        ci = caller_info()
        logger.info('CALL: ' + ci)
        print('***' + ci + ':')
        print(asciibox((toolname+'(',) + args, kwargs=kwargs))
        res = tool(*args, **kwargs)
        print('...' + ci + '.')
        return res

    decorated.__doc__ = '%(toolname)s tool (decorated)' % locals()
    return decorated

def message(context, message, messageType='info', mapping=None):
    """
    Ersetzt den gleichnamigen Tomcom-Adapter
    """
    pu = getToolByName(context, 'plone_utils')
    pu.addPortalMessage(pmf(safe_decode(message),
                            mapping=mapping),
                        messageType)

def getMessenger(context, decode=safe_decode):
    """
    Return a 'message' function which doesn't require
    (nor accept) a context argument
    """
    pu = getToolByName(context, 'plone_utils')
    apm = pu.addPortalMessage
    def message(message, messageType='info', mapping=None):
        """
        Ersetzt den gleichnamigen Tomcom-Adapter
        """
        apm(pmf(decode(message),
                mapping=mapping),
            messageType)
    return message


def getbrain(context, uid):
    """
    Ersetzt den gleichnamigen Tomcom-Adapter
    """
    pc = getToolByName(context, 'portal_catalog')._catalog
    brains = pc(UID=uid)
    if brains:
        return brains[0]


def make_brainGetter(context):
    """
    Return a function which looks up a UID
    and doesn't take a content argument;
    use this for multiple searches
    """
    pc = getToolByName(context, 'portal_catalog')._catalog

    def getbrain(uid):
        brains = pc(UID=uid)
        if brains:
            return brains[0]
    return getbrain


def make_pathByUIDGetter(context):
    """
    Return a function which looks up a UID
    and returns the path as stored in portal_catalog
    """
    pc = getToolByName(context, 'portal_catalog')._catalog
    indexes = pc.indexes

    def uid2path(uid):
        return indexes['path']._unindex[indexes['UID']._index[uid]]
            
    return uid2path


def make_timeformatter(context, **kwargs):
    util = getToolByName(context, 'translation_service')
    longFormat = kwargs.pop('longFormat', False)
    domain = kwargs.pop('domain', 'plonelocales')
    check_kwargs(kwargs)  # raises TypeError if necessary
    default_context = context
    func = util.ulocalized_time
    default_request = context.REQUEST

    def totime(time, longFormat=longFormat,
               context=None,
               domain='plonelocales',
               request=None):
        if not time:
            return None
        if context is None:
            context = default_context
        if request is None:
            request = default_request
        return func(time, longFormat,
                    context=context,
                    domain=domain,
                    request=request)

    return totime


def getPath(context, sep='/'):
    """
    Return the complete path from the Zope root.

    Without the sep option given, this is the same as the getPath mothod
    of Products.ZCatalog.CatalogPathAwareness.CatalogAware.
    """
    return sep.join(context.getPhysicalPath())


def parents(context):
    """
    Ersetzt den gleichnamigen Tomcom-Adapter
    """
    return context.REQUEST['PARENTS']


def parent_brains(context, parent=None, reverse=False):
    """
    Return the parents (as catalogued), as a list of brains

    parent -- the starting point (default: `context`)
    reverse -- return a reverted list? (default: False)
    """
    liz = []
    if not parent:
        if context.portal_type == 'Plone Site':
            return liz
        uid = context.UID()
        parent = getbrain(context, uid)

    while parent and parent.UID:
        liz.append(parent)
        parent = parent.getParent()
    if reverse:
        liz.reverse()
    return liz


def get_parent(context, **kwargs):
    """
    Return the nearest principia-folderish parent.

    Arguments:
      context -- the starting point

    Keyword-only:

      _as -- 'object' (default) or 'path', so far

      factory -- a function which takes an ancestor object
    """
    pop = kwargs.pop
    _as = pop('_as', None)
    func = pop('factory', None)
    if _as is not None:
        if func is not None:
            raise TypeError('Please specify *either* _as (%(_as)r) '
                            ' *or* factory (%(factory)r), '
                            'but not both!'
                            % locals())
        if _as == 'path':
            func = getPath
        elif _as == 'object':
            pass
        else:
            raise ValueError('Invalid _as spec %(_as)r'
                             % locals())
    check_kwargs(kwargs)  # raises TypeError if necessary
    for ancestor in context.REQUEST['PARENTS']:
        if getattr(ancestor, 'isPrincipiaFolderish', False):
            if func is None:
                return ancestor
            return func(ancestor)


def get_published_templateid(context):
    """
    Return the template id, as of the PUBLISHED variable, or None
    """
    request = context.REQUEST
    if request.has_key('PUBLISHED'):
        return request['PUBLISHED'].__name__
    return None
