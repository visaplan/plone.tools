# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
visaplan.plone.tools.search - search helpers
"""
# Python compatibility:
from __future__ import absolute_import, print_function

from six import text_type as six_text_type

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"
VERSION = (0,
           2,   # normalizeQueryString
           )

__all__ = [
        'normalizeQueryString',  # created by factory:
        'make_querystring_normalizer',
        'language_spec',
        ]

try:
    # Zope:
    from Products.CMFCore.utils import getToolByName
except ImportError:
    if __name__ == '__main__':
        class MockLanguageTool(object):
            def listSupportedLanguages():
                return [('en', 'English'), ('de', 'Deutsch')]
        def getToolByName(context, name):
            if name == 'portal_languages':
                return MockLanguageTool
    else:
        raise

# visaplan:
from visaplan.tools.lands0 import list_of_strings

try:
    # visaplan:
    from visaplan.tools.coding import safe_decode
except (ImportError, ValueError):
    if __name__ == '__main__':
        safe_decode = six_text_type
        print('Install visaplan.tools to properly test the normalizeQueryString function!')
    else:
        raise


def make_querystring_normalizer(decode=safe_decode):
    r"""
    Factory to create a `normalizeQueryString` function,
    injecting the default decoding function;
    by default, the safe_decode function from visaplan.tools is used,
    which (or course) recognizes unicode strings and decodes UTF8 and Latin-1.

    You may want to replace this `decode` argument by your own function,
    e.g. to

    - raise an exception if a non-unicode string is given,
      or
    - log calls which use non-unicode strings (to help during development)

    This factory is called by the module code to create the default
    `normalizeQueryString` function:

    >>> normalizeQueryString = make_querystring_normalizer(safe_decode)

    ... which will accept a string (and optionally another decoding function)
    and return a (possibly empty) list of unicode strings.

    For empty input, an empty list is returned:

    >>> normalizeQueryString('')
    []
    >>> normalizeQueryString(u'')
    []
    >>> normalizeQueryString('   \t \n \r')
    []

    There is special handling for the asterisk character ("*"):

    - If it is not present anywhere in the (non-empty) input string,
      it is added to the beginning and end of every string:

      >>> normalizeQueryString('abc')
      [u'*abc*']
      >>> normalizeQueryString(u'abc')
      [u'*abc*']
      >>> normalizeQueryString('   abc\t  def  ')
      [u'*abc*', u'*def*']
      >>> normalizeQueryString('entkoppelte Förderschnecke ')
      [u'*entkoppelte*', u'*F\xf6rderschnecke*']

    - If it *is* contained somewhere, we assume the user to do this on purpose,
      and thus don't amend the asterisk anywhere:

      >>> normalizeQueryString('ab*c')
      [u'ab*c']
      >>> normalizeQueryString('rohr* leitung  ')
      [u'rohr*', u'leitung']

    - a single-word asterisk is removed and simply causes the asterisk
      amemdments to be suppressed:

      >>> normalizeQueryString('rohr * leitung  ')
      [u'rohr', u'leitung']

    - Of course, a single asterisk *only* is like no search expression at all:

      >>> normalizeQueryString('  * ')
      []
    """
    def normalizeQueryString(string, decode=decode):
        """
        Return a (possibly empty) list of unicode strings.

        Arguments:

          string -- a string of some kind
          
          decode -- a function to check and, if necessary,
                    decode the given string 
        """
        # searchstring is None or empty
        if not string:
            return []

        if not isinstance(string, six_text_type):
            string = decode(string)
        if string.strip() == u'*':
            return []
        has_asterisk = u'*' in string
        strings = string.split()
        if has_asterisk or u'*' in strings:
            # ein alleinstehendes Asterisk würde *immer* passen;
            # also nur zur Unterdrückung der Automatik nutzen:
            return [s for s in strings
                    if s != u'*'
                    ]
        else:
            return [s.join((u'*', u'*'))
                    for s in strings
                    ]

    return normalizeQueryString
normalizeQueryString = make_querystring_normalizer(safe_decode)


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
    values = set(list_of_strings(value))
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
                language_tool = getToolByName(context, 'portal_languages')
            all_languages = [tup[0]
                             for tup in language_tool.listSupportedLanguages()
                             ]
        values.update(all_languages)
    return sorted(values)


if __name__ == "__main__":
    # Standard library:
    import doctest
    doctest.testmod()
