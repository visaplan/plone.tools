# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Kontext-Helferlein:

Funktionen, die im Rahmen eines Aufruf-Kontexts hilfreich sind
(also nicht über den aktuellen Request hinaus)
"""

# Standardmodule:
from traceback import extract_stack
import logging

# Plone:
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as pmf

# Unitracc-Tools:
from visaplan.plone.tools.log import getLogSupport
from visaplan.tools.minifuncs import gimme_False
from visaplan.tools.debug import log_or_trace
from visaplan.tools.debug import asciibox


__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           4,   # getActiveLanguage
           )

__all__ = ['getActiveLanguage',
           'make_permissionChecker',
           'make_timeFormatter',
           'make_userdetector',
           'make_SessionDataProxy',
           'message',
           'getbrain',
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


def make_permissionChecker(context=None, getAdapter=None,
                           checkperm=None, verbose=None):
    """
    Erzeuge eine Funktion, die eine übergebene Berechtigung prüft
    und einen Wahrheitswert zurückgibt.

    Achtung - unbekannte (z. B. falsch geschriebene) Bezeichnungen zeitigen
    keinen Fehler, sondern den Rückgabewert False!
    """
    if checkperm is None:
        if getAdapter is None:
            if context is None:
                raise ValueError('At least the context is needed!')
            getAdapter = context.getAdapter
        checkperm = getAdapter('checkperm')

    if verbose:
        # bisher nur mit Modul-, nicht mit Funktions-/Methodeninformation:
        logger = getLogSupport(stack_limit=4)[0]
        log = logger.info
        def cp_verbose(perm):
            val = checkperm(perm)
            log('checkperm(%(perm)r) --> %(val)r', locals())
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
    elif isinstance(ids, basestring):
        ids = ids.split(splitter)
        if not ids:
            return gimme_False
    IDS = frozenset(ids)
    if verbose is None:
        verbose = (splitter is not None
                   and len(splitter) > 1
                   )
    if verbose:
        print '*' * 79
        print 'make_userdetector(%s)' % arginfo(sorted(IDS), getid=getid)
        print '*' * 79

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
            if getAdapter is None:  # Schluß mit lustig:
                context = kwargs['context']
                getAdapter = context.getAdapter
            auth = getAdapter('auth')
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
    print '*** ' + ci
    print '*** getting tool %(toolname)r' % locals()

    tool = getToolByName(context, toolname)
    def decorated(*args, **kwargs):
        ci = caller_info()
        logger.info('CALL: ' + ci)
        print '***' + ci + ':'
        print asciibox((toolname+'(',) + args, kwargs=kwargs)
        res = tool(*args, **kwargs)
        print '...' + ci + '.'
        return res

    decorated.__doc__ = '%(toolname)s tool (decorated)' % locals()
    return decorated

def message(context, message, messageType='info', mapping={}):
    """
    Ersetzt den gleichnamigen Tomcom-Adapter
    """
    pu = getToolByName(context, 'plone_utils')
    pu.addPortalMessage(pmf(unicode(message),
                            mapping=mapping),
                        messageType)


def getbrain(context, uid):
    """
    Ersetzt den gleichnamigen Tomcom-Adapter
    """
    pc = getToolByName(context, 'portal_catalog')._catalog
    brains = pc(UID=uid)
    if brains:
        return brains[0]
