# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
Search Tools - Unterstützung für Suchfunktionen
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           1,   # initial version
           )

from visaplan.tools.lands0 import list_of_strings


def language_spec(value=None, form=None, context=None,
                  language_tool=None,
                  default_to_all=True,
                  all_languages=None):
    r"""
    Gib den korrekten Suchausdruck für die Einschränkung auf bestimmte
    Sprachversionen zurück.

    Argumente (bitte sämtlich benannt angeben!):

    value -- der Wert, falls schon ermittelt (None, String oder Sequenz)
    form -- das form-dict, falls nicht <value> angegeben; ggf. aus dem
            <context> ermittelt
    context -- kann ggf. verwendet werden, um das <language_tool> und/oder
               <form> zu ermitteln
    all_languages -- der Wert, der im Falle des Vorkommens von "all" im <value>
                     hinzugefügt wird; Unterdrücken z. B. durch Angabe von []
    default_to_all -- soll bei leerer oder fehlender Angabe eine
                      sprachunabhängige Suche ausgeführt werden?
                      (zu überlegen ist dann, ob *überhaupt* eine Angabe
                      benötigt wird.  Vielleicht ja, wegen etwaiger
                      Default-Mechanismen in aufgerufenen Funktionalitäten ...)

    >>> kwargs={'all_languages': ['de', 'en']}
    >>> language_spec(value='', **kwargs)
    ['de', 'en']
    >>> language_spec(value='all', **kwargs)
    ['de', 'en']
    >>> language_spec(value=['all', 'fr'], **kwargs)
    ['de', 'en', 'fr']

    'all' wird auch mit Leerraum erkannt:
    >>> language_spec(value=' all\n', **kwargs)
    ['de', 'en']

    Wenn der <value> nicht übergeben wird, wird er der <form>-Variablen
    'language' entnommen:

    >>> form={'language': 'de'}
    >>> kwargs.update({'form': form})
    >>> language_spec(**kwargs)
    ['de']

    Um ggf. eine leere Liste zu erhalten, muß default_to_all=False angegeben
    werden:

    >>> kwargs.update({'default_to_all': False})
    >>> language_spec(**kwargs)
    ['de']
    >>> language_spec(value='', **kwargs)
    []
    """
    if value is None:
        if form is None:
            form = context.REQUEST.form
        try:
            value = form['language']
        except KeyError:
            value = []
    # print '*** language_spec: value=%(value)r' % locals()
    values = set([s2 for s2 in
                     [s.strip() for s in list_of_strings(value)]
                  if s2
                  ])
    try:
        values.remove('all')
    except KeyError:
        if values:
            has_all = False
        else:
            has_all = default_to_all
    else:
        has_all = True
    if has_all:
        if all_languages is None:
            if language_tool is None:
                language_tool = context.getAdapter('pl')()
            all_languages = [tup[0]
                             for tup in language_tool.listSupportedLanguages()
                             ]
        values.update(all_languages)
    # print '*** language_spec --> sorted(%(values)r)' % locals()
    return sorted(values)


NONTHUMBNAIL_PORTALTYPES = ['UnitraccTable',
                            ]
def queries_nonthumbnail_types_only(query):
    """
    Die übergebene Suche spezifiziert Typen, und zwar ausschließlich solche,
    die explizit keine sinnvollen Vorschaubilder haben

    (für die lokale Suche)
    """
    try:
        pt_spec = query['portal_type']
    except KeyError:
        return False
    else:
        if isinstance(pt_spec, basestring):
            pt_spec = [pt_spec]
        vals = set()
        for pt in pt_spec:
            vals.add(pt in NONTHUMBNAIL_PORTALTYPES)
        if len(vals) != 1:
            return False
        return list(vals)[0]  # Wert des einzigen Elements


