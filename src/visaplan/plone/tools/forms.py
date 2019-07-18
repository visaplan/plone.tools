# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Tools für Formulare
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"


# Standardmodule
from urlparse import urlsplit, urlunsplit
from urllib import urlencode
from cgi import parse_qsl
from collections import defaultdict
from string import strip
from datetime import date
from time import strptime

# Installierte Module:
from bs4 import BeautifulSoup

# Unitracc-Tools
try:
    from visaplan.tools.lands0 import as_new_list
    from visaplan.plone.tools.functions import is_uid_shaped
except ImportError:
    if __name__ == '__main__':
        print('Some tests will fail due to import problem')
    else:
        raise
    UIDCHARS_UNICODE = frozenset(u'0123456789abcdef')
    def is_uid_shaped(s, onerror='raise'):
        if isinstance(s, str):
            try:
                s = s.decode('ascii')
            except UnicodeDecodeError:
                return False
        elif isinstance(s, unicode):
            pass
        elif onerror == 'raise':
            raise ValueError('String expected: %(s)r'
                             % locals())
        else:
            return False
        return len(s) == 32 and UIDCHARS_UNICODE.issuperset(s)
    def as_new_list(val, splitfunc=None):
        if val is None:
            return []
        if not isinstance(val, basestring):
            return list(val)
        if splitfunc is None:
            return [s.strip() for s in val.split(',')]
        return splitfunc(val)
# (mit ../../scripts/run-doctests klappt der Export;
# bei direktem Aufruf mit python oder zopepy funktionieren
# wenigstens die Tests, die weder MockRequest noch is_uid_shaped
# benötigen)
try:
    from .mock import MockRequest
except (ImportError, ValueError):
    if __name__ != '__main__':
        raise

__all__ = ('tryagain_url',
           'back_to_referer',
           'merge_qvars',
           # -------------------- [ nun in visaplan.tools.lands0 ... [
           # 'list_of_strings',
           # 'string_of_list',
           # 'as_new_list',
           # 'lines_to_list',
           # -------------------- ] ... nun in visaplan.tools.lands0 ]
           # --------------------- [ nun in visaplan.tools.dicts ... [
           # 'subdict',
           # 'subdict_onekey',
           # 'subdict_forquery',
           # --------------------- ] ... nun in visaplan.tools.dicts ]
           'sorted_flaglist',
           'dict_from_form',
           'get_dict',
           'restricted_default',
           'form_default__factory',
           # ----------------- [ nun in visaplan.tools.minifuncs ... [
           # 'gimme_None',
           # 'gimme_True',
           # 'gimme_False',
           # 'gimmeConst__factory',
           # ----------------- ] ... nun in visaplan.tools.minifuncs ]
           # --------------------- [ nun in visaplan.tools.dates ... [
           # 'make_date_parser',
           # 'parse_date',
           # --------------------- ] ... nun in visaplan.tools.dates ]
           'detect_duplicates',
           'uid_or_number',
           # HTML-Code erzeugen:
           'make_input',
           # --------------------- [ nun in visaplan.tools.dicts ... [
           # 'updated',
           # --------------------- ] ... nun in visaplan.tools.dicts ]
           )

# hier nicht mehr verwendet, wg. urlsplit;
# wird demnächst entfallen:
QUERY_ONLY_CHARS = frozenset('?&=')


def tryagain_url(request, varnames=None,  # ----- [ tryagain_url ... [
                 path=None,
                 # bitte stets benannt angeben:
                 var_items=None,
                 use_suffix=None,
                 use_first=None):
    """
    Umleitung zur sendenden Seite, um es nochmal zu probieren.

    request -- das Request-Objekt mit form-Dictionary und HTTP_REFERER
    varnames -- Positivliste von Variablen für den Query-String
    path -- Pfad zu einer zu verwendenden Seite/Methode;
            darf keine Fragezeichen o.ä. enthalten
            (als absolute Angabe interpretiert)

    ACHTUNG: Ab visaplan.plone.tools 1.2 müssen alle Argumente außer dem ersten
             (<request>) benannt übergeben werden!
    NOTE: Starting from visaplan.plone.tools 1.2, all arguments except the first
          one (the request) must be given by name!

    >>> req = MockRequest('http://test.me/desktop/tan', tan='123',
    ...                   date='1.1.1970', other='ignoreme')
    >>> tryagain_url(req, ['tan', 'date'])
    'http://test.me/desktop/tan?tan=123&date=1.1.1970'
    >>> tryagain_url(req, ['tan', 'date'], 'schreibtisch/mytan')
    'http://test.me/schreibtisch/mytan?tan=123&date=1.1.1970'

    Von einem übergebenen Pfad <path> wird nur die Pfadkomponente verwendet,
    nicht jedoch ein etwa enthaltener Hostname usw.:

    >>> tryagain_url(req, ['tan', 'date'],
    ...              'http://www.test.me/nur/der/pfad')
    'http://test.me/nur/der/pfad?tan=123&date=1.1.1970'
    >>> tryagain_url(req, ['tan'],
    ...              'manage_xy')
    'http://test.me/manage_xy?tan=123'

    Für Listenwerte ist das Standardverhalten, dem Variablennamen das Suffix
    ':list' anzuhängen und alle nicht-leeren Werte zu verwenden:
    >>> req = MockRequest('http://test.me/desktop/tan',
    ...                   ids=['eins', '', 'zwei'])
    >>> tryagain_url(req, ['ids'])
    'http://test.me/desktop/tan?ids%3Alist=eins&ids%3Alist=zwei'

    Dies kann sich noch ändern; die Sinnhaftigkeit solcher URLs wurde noch
    nicht überprüft!

    Wenn use_first angegeben wird, wird nur der jeweils erste nicht-leere Wert
    weitergereicht, und ':list' wird per default nicht verwendet:
    >>> tryagain_url(req, ['ids'], use_first=True)
    'http://test.me/desktop/tan?ids=eins'

    Alternativ zur Angabe der Variablennamen ist es auch möglich,
    die zu verwendenden Variablen mit ihren Werten zu übergeben:
    >>> tryagain_url(req, var_items=[('name', 'value')])
    'http://test.me/desktop/tan?name=value'
    """
    referer = request['HTTP_REFERER']
    su = list(urlsplit(referer))
    qsl = []
    form = request.form
    if var_items is not None:
        if varnames is not None:
            raise TypeError('Specify *either* varnames *or* var_items!')
        if not isinstance(var_items, list):
            qsl.extend(list(var_items))
        else:
            qsl.extend(var_items)
    if varnames is None:
        varnames = []
    for name in varnames:
        val = form.get(name, None)
        # print 'tryagain_url: %(name)r, %(val)r' % locals()
        if val:
            if isinstance(val, basestring):
                qsl.append((name, val.strip()))
            elif isinstance(val, (list, tuple)):
                # done = False
                if use_suffix is None:
                    use_suffix = not use_first
                if use_suffix:
                    name += ':list'
                for chunk in val:
                    if chunk:
                        qsl.append((name, chunk))
                        if use_first:
                            # done = True
                            break
            else:
                qsl.append((name, str(val)))
    su[3] = urlencode(qsl)
    su[4] = ''
    if path:
        # (--> scheme, netloc, path, query, fragment):
        parsed_path = urlsplit(path)
        path = parsed_path.path
        if path:
            su[2] = path
    return urlunsplit(su)
    # ------------------------------------------- ] ... tryagain_url ]


def back_to_referer(context=None,  # --------- [ back_to_referer ... [
                    request=None, url=None,
                    detect_browser=None,
                    redirect=True,
                    items=(),
                    **kwargs):
    """
    Die übliche Umleitung zur verweisenden Seite.

    Standardverwendung:

        return back_to_referer(context)

    am Ende von Browser-Methoden; alle Optionen (außer einem als erstes
    übergebenen Kontext) werden benannt übergeben.

    Modifikation der URL, typischerweise des Referers:
    Es können entweder <items> angegeben werden (eine Sequenz von 2-Tupeln)
    oder benannte Argumente.

    Optionen:
      context - üblicherweise vorhanden und, sofern nicht ohnehin der Request
                verwendet wurde, als unbenanntes Argument übergeben
      request - der eigentlich interessierende Teil des Kontexts.
                Wenn ermittelt, als benanntes Argument übergeben.
      url -     z. B. ein Methodenname.
        ACHTUNG: Es findet keinerlei Behandlung für Query-Strings etc.
                 statt!
      detect_browser -- neu, und daher *vorerst* per Vorgabe nicht aktiv:
                stelle fest, ob der Request '/@@' enthält (--> dann fehlt ein
                korrekter Kontext!) und entfernt ggf. alles ab dieser
                Zeichenkette
      redirect - nur für die Testbarkeit gedacht
      items -   Sequenz von (Variable, Wert)-Tupeln für den Query-String

    Die Option <redirect> dient allein der Testbarkeit:

    >>> req = MockRequest('http://test.me/transmin',
    ...                   actual_url='http://test.me/@@mogrify/import_tarball')
    >>> def b2r_url(context=None, **kwargs):
    ...     kwargs['redirect'] = False
    ...     return back_to_referer(context, **kwargs)

    Ohne detect_browser (aktuelles Standardverhalten) wird die übergebene "url"
    (d.h., meistens nur der Name einer Sicht) direkt verwendet; der Nutzwert
    besteht dann in der Ausführung der Umleitung:

    >>> b2r_url(request=req, url='formname', detect_browser=False)
    'formname'

    Wenn eine Browser-Methode ausgeführt wird, ist das mutmaßlich nicht gut
    genug; die relative Umleitung wird von Zope nicht auf der Basis des Referers
    ausgeführt, sondern der Methode im Kontext. Um eine Umleitung nach
    .../@@browsername/formname zu vermeiden (ohne gültigen Kontext!),
     detect_browser=True angeben:

    >>> b2r_url(request=req, url='formname', detect_browser=True)
    'http://test.me/formname'

    """
    if request is None:
        request = context.REQUEST
    url_given = url is not None
    if url is None:
        url = request['HTTP_REFERER']
        if detect_browser is None:
            detect_browser = False  # Bleibt womöglich
    elif detect_browser is None:
        detect_browser = False  # --- Vorerst - kann sich ändern!
    if detect_browser:
        actual_url = request['ACTUAL_URL']
        if '/@' in actual_url:
            parsed_path = urlsplit(actual_url)
            ppli = list(parsed_path)
            ppp = parsed_path.path
            po = ppp.find('/@@')
            if po == 0:
                if url_given:
                    ppli[2] = '/' + url.lstrip('/')
                else:
                    ppli = list(urlsplit(url))  # der Referer
            elif po != -1:
                if url_given:
                    ppli[2] = ppp[:po+1] + url.lstrip('/')
                else:
                    ppli[2] = ppp[:po]
            url = urlunsplit(ppli)

    if items:
        assert not kwargs
        url = merge_qvars(url, items)
    elif kwargs:
        url = merge_qvars(url, kwargs)
    if not redirect:
        return url
    # print '*** Umleitung -->', url
    return request.RESPONSE.redirect(url)
    # ---------------------------------------- ] ... back_to_referer ]


def merge_qvars(url, items):  # ------------------ [ merge_qvars ... [
    """
    Ergänze eine als String übergebene URL durch die übergebenen
    Query-Variablen.

    >>> merge_qvars('http://test.me/here', (('eins', 1),))
    'http://test.me/here?eins=1'
    >>> merge_qvars('http://test.me/here?eins=0', (('eins', 1),))
    'http://test.me/here?eins=1'
    >>> merge_qvars('http://test.me/here?eins=1', (('zwei', 2),))
    'http://test.me/here?eins=1&zwei=2'

    Es kann auch ein dict-Objekt übergeben werden; in diesem Falle
    werden dessen Schlüssel sortiert:

    >>> merge_qvars('http://test.me/here', {'zwei': 2, 'drei': 3})
    'http://test.me/here?drei=3&zwei=2'

    Es ist möglich, eine Variable zu löschen,
    indem als Wert None übergeben wird:

    >>> merge_qvars('http://test.me/here?eins=0', (('eins', None),))
    'http://test.me/here'

    Die Variablennamen werden in folgender Reihenfolge berücksichtigt:
    - erst die schon in der URL vorhandenen, unter Beibehaltung der
      Reihenfolge;
    - dann die im items-Argument übergebenen (wenn eine Sequenz, unter
      Beibehaltung der gegebenen Reihenfolge; wenn ein dict, in
      ASCII-sortierter Folge)
    Es werden auch URLs ohne Hostkomponente unterstützt.

    >>> merge_qvars('methode?eins=1&zwei=2',
    ...             (('vier', 4), ('drei', 3)))
    'methode?eins=1&zwei=2&vier=4&drei=3'
    >>> merge_qvars('methode?eins=1&zwei=2',
    ...             {'vier': 4, 'drei': 3})
    'methode?eins=1&zwei=2&drei=3&vier=4'

    Mehrfach vergebene Variablennamen werden - nach der Logik der Initiali-
    sierung eines Dictionarys aus einer Sequenz von (key, val)-Tupeln - auf
    den letzten enthaltenen Wert reduziert;
    es gibt keinerlei Listenfunktionalität.

    Wenn Listen erhalten bleiben sollen, ist dafür eine spezielle Funktion
    nötig!

    Hier ein Beispiel zur Illustration, was implizit passiert:

    >>> merge_qvars('http://test.me/here?eins=0&eins=1', ())
    'http://test.me/here?eins=1'

    Da dieses Verhalten durchaus gewünscht sein und dazu genutzt werden kann,
    URLs zu "normalisieren", sollte es nicht leichtfertig geändert werden.
    """
    given_dic = dict(items)
    if isinstance(items, dict):
        items = sorted(items.items())
    given_url = urlsplit(url)
    changable = list(given_url)
    # in der geg. URL vorhandene Query-Variablen
    # (zunächst als Liste, um die Reihenfolge zu erhalten):
    query_lst = parse_qsl(given_url.query)
    query_dic = dict(query_lst)
    new_query = []
    query_dic.update(given_dic)
    # zuerst die vorhandenen, dann die gegebenen Variablen,
    # jeweils in Originalreihenfolge:
    for lst in (query_lst, items):
        for tup in lst:
            key, oldval = tup
            if key not in query_dic:
                continue
            val = query_dic.pop(key)
            if val is not None:
                new_query.append((key, val))
    changable[3] = urlencode(new_query)
    return urlunsplit(changable)
    # -------------------------------------------- ] ... merge_qvars ]


# ------------------------------- [ nun in visaplan.tools.lands0 ... [
# def list_of_strings(): hier gelöscht
# def string_of_list(): hier gelöscht
# def lines_to_list(): hier gelöscht
# def as_new_list(): hier gelöscht
# ------------------------------- ] ... nun in visaplan.tools.lands0 ]


# -------------------------------- [ nun in visaplan.tools.dicts ... [
# def subdict(): hier gelöscht
# def subdict_onekey(): hier gelöscht
# def subdict_forquery(): hier gelöscht
# -------------------------------- ] ... nun in visaplan.tools.dicts ]


def sorted_flaglist(val, keys, first=None, strict=True):
    """
    Z. B. um TTW gewählte Aktionen auszuwerten und in einer Sequenz von
    Checkboxen darzubieten:

    >>> sorted_flaglist('parse', ('parse', 'fix'))
    [('parse', True), ('fix', False)]

    Die in <first> angegebenen Schlüssel sind immer True:
    >>> sorted_flaglist('parse', ('parse', 'fix'), 'bonk')
    [('bonk', True), ('parse', True), ('fix', False)]
    """
    res = []
    val = as_new_list(val)
    first = as_new_list(first)
    done = set()
    for key in first:
        if key in done:
            continue
        res.append((key, True))
        done.add(key)
    for key in keys:
        if key in done:
            continue
        if key in val:
            res.append((key, True))
        else:
            res.append((key, False))
        done.add(key)
    if strict:
        return res
    for key in val:
        if key in keys or key in done:
            continue
        res.append((key, False))
        done.add(key)
    return res


def dict_from_form(form, name, names=None):
    """
    Lies ein dict aus dem Request;
    siehe <http://old.zope.org/Members/Zen/howto/FormVariableTypes>.

    Wir probieren zwei Varianten, ein dict per Formular zu erzeugen:

    - direkt: dann wird der Schlüsselname als Feldname verwendet
      (geht nur, wenn die Schlüsselnamen vorab bekannt sind, also
       serverseitig erzeugt werden);
    - über eine Liste von dicts; in diesem Fall müssen zwei Namen angegeben werden,
      um die Schlüssel und die Werte zuordnen zu können.

    >>> src = {'aslist': [{'key': 'eins', 'val': 'zwei'}],
    ...        'asdict': {'eins': 'zwei', 'drei': None},
    ...        }
    >>> dict_from_form(src, 'aslist', ('key', 'val'))
    {'eins': 'zwei'}
    >>> dict_from_form(src, 'asdict')
    {'eins': 'zwei'}
    """
    val = form.get(name)
    if not val:
        return {}
    if isinstance(val, (list, tuple)):
        # eine Sequenz von dicts:
        keyname, valname = names
        val = dict([(dic[keyname], dic[valname])
                    for dic in val])
    return {k: v
            for (k, v) in val.items()
            if v}


def get_dict(a, fork=False):
    """
    Gib ein übergebenes dict-Objekt zurück
    oder erzeuge es.

    Das Argument ist entweder schon ein dict-Objekt:

    >>> dic_a = {'a': 1}
    >>> dic_b = get_dict(dic_a)
    >>> dic_b is dic_a
    True
    >>> dic_c = get_dict(dic_a, True)
    >>> dic_c is dic_a
    False
    >>> dic_c == dic_a
    True

    ... oder eine Sequenz [f[, args][, kwargs]]
    mit einer Funktion f, die (hoffentlich; hier nicht überprüft!)
    mit f(*args, **kwargs) ein dict-Objekt erzeugt:

    >>> get_dict([dict])
    {}
    >>> get_dict([dict, ((('b', 2),),)])
    {'b': 2}

    >>> def df(a, b):
    ...   return locals()
    >>> get_dict([df, (11,), {'b': 22}])
    {'a': 11, 'b': 22}
    """
    if isinstance(a, dict):
        if fork:
            return dict(a)
        return a

    has_args = False
    has_kwargs = False
    needs_func = True
    f = None
    args = ()
    kwargs = {}
    for arg in a:
        if needs_func:
            f = arg
            needs_func = False
        elif isinstance(arg, tuple):
            if has_args:
                raise ValueError('%(f)r(%(arg)r): ist zuviel'
                                 % locals())
            args = arg
            has_args = True
        elif isinstance(arg, dict):
            if has_kwargs:
                raise ValueError('%(f)r(%(arg)r): ist zuviel'
                                 % locals())
            kwargs = arg
            has_kwargs = True
        else:
            raise ValueError('%(f)r(%(arg)r): Tupel oder dict erwartet'
                             % locals())
    return f(*args, **kwargs)


def restricted_default(form, key, choices, default=None):
    """
    Gib den Wert für den Schlüssel <key> zurück, sofern er in <choices>
    enthalten ist; ansonsten <default>.

    >>> form = {'action': 'view',
    ...         'evil': 'erase_all'}
    >>> choices = ('create', 'edit', 'view')
    >>> restricted_default(form, 'action', choices)
    'view'
    >>> restricted_default(form, 'evil', choices)
    """
    val = form.get(key)
    if val in choices:
        return val
    return default


def form_default__factory(form, key, choices):
    # shallow copy sollte reichen:
    saved = dict(form)
    def given_or_default(default):
        return restricted_default(saved, key, choices, default)
    return given_or_default


# ---------------------------- [ nun in visaplan.tools.minifuncs ... [
# def gimme_None(): hier gelöscht
# def gimme_True(): hier gelöscht
# def gimme_False(): hier gelöscht
# def gimmeConst__factory(): hier gelöscht
# ---------------------------- ] ... nun in visaplan.tools.minifuncs ]


# -------------------------------- [ nun in visaplan.tools.dates ... [
# def make_date_parser(): hier gelöscht
# parse_date = make_date_parser()
# -------------------------------- ] ... nun in visaplan.tools.dates ]

def detect_duplicates(*args, **kwargs):
    """
    Stelle fest, ob ein oder mehrere Werte der Sequenzvariablen <varname>
    mehrfach vorkommen; das kann bei Zope-Formularen zur Konsequenz haben, daß
    andere Werte unerwarteterweise als Listen ankommen.

    Wenn die Variable bereits ausgelesen wurde, kann der einfachste Aufruf
    verwendet werden:
    >>> list(detect_duplicates('a b c a'.split()))
    ['a']

    Ansonsten werden benannte Argumente benötigt, z. B.:

    >>> list(detect_duplicates('ids', form={'ids': 'a a a b b c'.split()}))
    ['a', 'b']

    - form -- das Formularobjekt. Wenn übergeben, wird ein etwaiges unbenanntes
              Argument als <varname> interpretiert, sonst als <values>;
              wenn <values> fehlt, muß <form> einen Schlüssel <varname>
              enthalten
    - context -- der Kontext
    - varname -- der Name der Variablen.
                 <form> wird benötigt und ggf. aus <context> ermittelt.
    - values -- ./. varname

    """
    form = kwargs.pop('form', None)
    context = kwargs.pop('context', None)
    try:
        values = kwargs.pop('values')
    except KeyError:
        try:
            varname = kwargs.pop('varname')
        except KeyError:
            # weder values noch varname explizit angegeben.
            # Wenn <form> explizit angegeben wurde,
            # wird das unbenannte erste Argument als <varname> interpretiert,
            # sonst als <values>
            # (und wenn es nicht existiert, tritt ein Fehler auf):
            if form is not None:
                varname = args[0]
                values = form[varname]
            else:
                values = args[0]
            assert not args[1:]
        else:                 # varname angegeben,
            if form is None:  # form nicht: context muß vorhanden sein
                form = context.REQUEST.form
            values = form[varname]   # ohne <values>
            assert not args
    else:
        assert 'varname' not in kwargs
        assert not args

    if isinstance(values, basestring):
        raise ValueError('Variable %(varname)s contains a string'
                         ' (sequence expected): %(values)r'
                         % locals())
    cnt = defaultdict(int)
    for val in values:
        cnt[val] += 1
        if cnt[val] == 2:
            yield val


def uid_or_number(val, **kwargs):
    """
    Gib ein dict zurück mit den Schlüsseln 'uid', 'number' und 'prefix';
    diese Schlüssel werden je nach Eingabewert befüllt:

    >>> uid_or_number('42')['number']
    42
    >>> uid_or_number('12345678123456781234567812345678')['uid']
    '12345678123456781234567812345678'

    Als Eingabewerte werden auch Ganzzahlen akzeptiert:
    >>> uid_or_number(42)['number']
    42

    Die notorischen Präfixe ('uid-', 'rel-') werden erkannt:
    >>> dic = uid_or_number('rel-12345678123456781234567812345678')
    >>> sorted(dic.items())
    [('number', None), ('prefix', 'rel-'), ('uid', '12345678123456781234567812345678')]

    Um die Fehlinterpretation von UIDs als Zahlen zu unterbinden, gibt es ein
    <limit> für konvertierte Zahlen:
    >>> uid_or_number('10001')
    Traceback (most recent call last):
        ...
    ValueError: 10001 exceeds the limit! (10000)

    Das Limit kann explizit angegeben oder auch aufgehoben werden:
    >>> uid_or_number('10001', limit=None)['number']
    10001

    Wenn eine Zahl übergeben wurde, gibt es keine solche Beschränkung:
    >>> uid_or_number(10001)['number']
    10001
    """
    res = {'uid':    None,
           'number': None,
           'prefix': '',
           }
    if val is None:
        return res
    elif isinstance(val, int):
        res['number'] = val
        return res
    liz = val.split('-', 1)
    if liz[1:]:
        res['prefix'] = liz[0] + '-'
        val = liz[1]
    num = None
    try:
        num = int(val)
        limit = kwargs.pop('limit', 10000)
        if limit is not None and num > limit:
            raise ValueError('%(num)r exceeds the limit! (%(limit)r)'
                             % locals())
        res['number'] = num
    except ValueError:
        if is_uid_shaped(val):
            res['uid'] = val
        else:
            raise
    return res


def make_input(data, **kwargs):
    """
    Erzeuge HTML-input-Elemente für die übergebenen Daten <data>.

    Das optionale Schlüsselwortargument <type> gibt den Typ an (Vorgabe:
    "hidden");
    sonstige Schlüsselwortargumente werden an den BeautifulSoup-Konstruktor
    übergeben; hier für die Doctests:
    >>> kw={'features': 'html.parser'}

    Hauptzweck ist es, hidden-Felder zu erzeugen:
    >>> make_input({'getCustomSearch': ['portal_type=UnitraccImage']}, **kw)
    '<input name="getCustomSearch:list" type="hidden" value="portal_type=UnitraccImage"/>'
    >>> make_input({'depth': 3}, **kw)
    '<input name="depth:int" type="hidden" value="3"/>'

    Für leere Listen wird dennoch ein (leerer) Eintrag erzeugt
    (sofern nicht irgendwie ignore_empty angezeigt ist; derartiges ist hier
    aber noch nicht implementiert)

    >>> make_input({'emptylist': []}, **kw)
    '<input name="emptylist:list" type="hidden" value=""/>'

    Der hidden-Typ kann durch explite Angabe einer "falschen" type-Option
    unterdrückt werden:
    >>> make_input({'getCustomSearch': ['portal_type=UnitraccImage']}, type=None, **kw)
    '<input name="getCustomSearch:list" value="portal_type=UnitraccImage"/>'
    """
    # TODO: leere Elemente (Whitelist/Blacklist, :ignore_empty);
    #       vermutlich mit anderer Funktionssignatur oder Funktions-Factory
    if not data:
        return None
    # das klappt nicht: (!)
    # assert isinstance(data, dict), \
    #       'dictionary expected (%r)' % (data,)
    type = kwargs.pop('type', 'hidden')
    if type:
        def attr_dict(name, value):
            return {'name': name,
                    'value': str(value),
                    'type': type,
                    }
    else:
        def attr_dict(name, value):
            return {'name': name,
                    'value': str(value),
                    }
    if kwargs and 0:
        raise TypeError('Currently all kwargs ignored! (%s)'
                        % (kwargs,))
    soup = BeautifulSoup(**kwargs)
    res = []
    for key, val in data.items():
        # Siehe http://old.zope.org/Members/Zen/howto/FormVariableTypes,
        # http://dev-wiki.unitracc.de/wiki/Typenkonversion_in_Zope-Formularen
        if isinstance(val, list):
            key += ':list'
            empty = True
            for thisval in val:
                if thisval not in ('', None):
                    empty = False
                    tag = soup.new_tag('input')
                    tag.attrs = attr_dict(key, thisval)
                    res.append(str(tag))
            if empty:  # XXX checkme; wo ist das dokumentiert?!
                tag = soup.new_tag('input')
                tag.attrs = attr_dict(key, '')
                res.append(str(tag))
        elif isinstance(val, basestring):
            tag = soup.new_tag('input')
            tag.attrs = attr_dict(key, val)
            res.append(str(tag))
        elif isinstance(val, int):
            key += ':int'
            tag = soup.new_tag('input')
            tag.attrs = attr_dict(key, val)
            res.append(str(tag))
        else:
            raise ValueError('make_input, key=%(key)r:'
                             ' type of %(val)r unsupported'
                             % locals())
    return '\n'.join(res)


# -------------------------------- [ nun in visaplan.tools.dicts ... [
# def updated(): hier gelöscht
# -------------------------------- ] ... nun in visaplan.tools.dicts ]


if __name__ == '__main__':
    class MockRequest(dict):
        # kopiert ins mock-Modul
        def __init__(self, referer=None, **kwargs):
            self['HTTP_REFERER'] = referer
            self['ACTUAL_URL'] = kwargs.pop('actual_url', referer)
            self.form = kwargs

    import doctest
    doctest.testmod()
