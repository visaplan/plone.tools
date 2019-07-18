# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
attools - Archetype tools
"""

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"

from collections import defaultdict

from zope import event
from Products.Archetypes.event import ObjectEditedEvent
from Products.Archetypes.utils import mapply, shasattr

from visaplan.tools.lands0 import makeSet


# <http://stackoverflow.com/a/35756881/1051649>;
# von maurits, <http://stackoverflow.com/users/621201/maurits>:
def initialize_rich_text_fields(instance):
    """New rich text fields should have mimetype text/html.

    Adapted from setDefaults in Archetypes BasicSchema.
    """
    default_output_type = 'text/x-html-safe'
    mimetype = 'text/html'
    schema = instance.Schema()
    for field in schema.values():
        # We only need to do this for fields with one specific mimetype.
        if not shasattr(field, 'default_output_type'):
            continue
        if field.default_output_type != default_output_type:
            continue
        # only touch writable fields
        mutator = field.getMutator(instance)
        if mutator is None:
            continue
        base_unit = field.getBaseUnit(instance)
        if base_unit.mimetype == mimetype:
            continue
        # If content has already been set, we respect it.
        if base_unit:
            continue
        default = field.getDefault(instance)
        args = (default,)
        kw = {'field': field.__name__,
              '_initializing_': True}
        kw['mimetype'] = mimetype
        mapply(mutator, *args, **kw)


def notifyedit(context):
    """
    trigger on-edited events for context
    """
    event.notify(ObjectEditedEvent(context))


# "Log-Level" für generierte Funktion::
BASE, CHANGE, NOP, SKIP, DEBUG = (1, 2, 3, 4, 99)

CORE_FIELDS = set([
        'id', 'title',
        ])
BOOLEAN_FIELDS = set([
        'excludeFromNav',
        'allowDiscussion',
        'excludeFromSearch',
        ])
DATE_FIELDS = set([
        'creation_date', 'modification_date',
        'effectiveDate', 'expirationDate',
        ])
UNITRACC_NUMERIC_FIELDS = set([
        'price_shop',
        'shopduration',
        ])
UNITRACC_CHOICES_FIELDS = set([
        'code',
        'unitraccGroups',
        'subPortals',
        ])
PLONE_OTHER_FIELDS = set([  # sonstige (Plone):
        'creators',
        'language',
        ])
UNITRACC_OTHER_FIELDS = set([
        # XML:
        'xml',
        # evtl. später doch berücksichtigen :
        'certificate',
        'contributors',
        'difficulty',
        'duration',
        'html_left',
        'html_right',
        'location',
        'price',
        'relatedItems',
        'subject',
        'target_group',
        ])
# Nicht nach HTML konvertieren:
DEFAULT_BLACKLIST = set()
DEFAULT_BLACKLIST.update(CORE_FIELDS)
DEFAULT_BLACKLIST.update(BOOLEAN_FIELDS)
DEFAULT_BLACKLIST.update(DATE_FIELDS)
DEFAULT_BLACKLIST.update(UNITRACC_NUMERIC_FIELDS)
DEFAULT_BLACKLIST.update(UNITRACC_CHOICES_FIELDS)
DEFAULT_BLACKLIST.update(PLONE_OTHER_FIELDS)
DEFAULT_BLACKLIST.update(UNITRACC_OTHER_FIELDS)


def make_minilogger(verbose, logger, prefix=None):
    """
    Erzeuge den Minilogger, üblicherweise tell(LEVEL, text[, mapping ...])
    """
    def make_mapping(*args):
        if not args:
            return {}
        elif (not args[1:]) and isinstance(args[0], dict):
            return args[0]
        else:
            return args

    if verbose:
        if logger is None:
            if prefix:
                MASK = prefix.replace('%', '%%') + ': %s'
                def _tell(s, *args):
                    print MASK % (s % make_mapping(*args))
            else:
                def _tell(s, *args):
                    print s % make_mapping(*args)
        else:
            _tell = logger.info
        def tell(level, s, *args):
            if verbose >= level:
                _tell(s, *args)
                return True
    else:
        def tell(level, s, *args):
            pass
    return tell


def make_skip_function(tell, **kwargs):
    """
    Gib eine skip-Funktion zurück, die Attributnamen mit der black- oder
    whitelist vergleicht
    """
    if ('sets' in kwargs
        and 'whitelist' not in kwargs
        and 'blacklist' not in kwargs
        ):
        sets = kwargs.pop('sets')
        if sets:
            def skip(fieldname):
                return fieldname not in sets
            return skip

    whitelist = kwargs.pop('whitelist', None)
    blacklist = kwargs.pop('blacklist', None)
    if whitelist is not None:
        assert blacklist is None
        if isinstance(whitelist, basestring):
            whitelist = [whitelist]
        whitelist = set(whitelist)
        def skip(fieldname):
            if fieldname not in whitelist:
                tell(SKIP, '%(fieldname)r not in whitelist --> SKIP', locals())
                return True
            return False
    else:
        if blacklist is None:
            blacklist = []
        elif isinstance(blacklist, basestring):
            blacklist = [blacklist]
        blacklist = set(blacklist)
        blacklist.update(DEFAULT_BLACKLIST)
        def skip(fieldname):
            if fieldname in blacklist:
                tell(SKIP, '%(fieldname)r in blacklist --> SKIP', locals())
                return True
            return False
    return skip


def instance_and_label(instance, brain, verbose):
    if instance is None:
        instance = brain.getObject()
        if verbose:
            iinfo = brain.getURL()
    elif verbose:
        iinfo = repr(instance)
    else:
        iinfo = None
    return instance, iinfo


def make_mimetype_fixer(**kwargs):
    """
    Erzeuge eine Funktion, die das übergebene Archetypes-Objekt korrigiert.

    Alle Optionen müssen als Schlüsselwortargument übergeben werden:

    from_mimetype  -- Vorgabe: keine Filterung
    to_mimetype -- Vorgabe: 'text/html'
    default_output_type -- Vorgabe: 'text/x-html-safe'

    counter -- üblicherweise ein defaultdict(int).  Wenn nicht übergeben, wird
               eines erzeugt, dessen Werte dann nicht zugänglich sind.
    verbose -- ausführliche Ausgaben/Logging?
    logger -- der zu verwendende Logger
    """
    # --------------------------- [ Argumente für die Ausführung ... [
    verbose = kwargs.pop('verbose', None)
    logger = kwargs.pop('logger', None)
    if verbose is None:
        verbose = logger is not None
    tell = make_minilogger(verbose, logger, 'fix_types')

    if 'counter' in kwargs:
        counter = kwargs.pop('counter')
    else:
        counter = defaultdict(int)

    # zu bearbeitende Attribute:
    skip = make_skip_function(tell, **kwargs)
    # --------------------------- ] ... Argumente für die Ausführung ]

    # --------------------------- [ Argumente für die Konversion ... [
    from_mimetypes = []
    from_mimetype = kwargs.pop('from_mimetype', None)
    if from_mimetype is None:
        from_mimetypes = None
    elif isinstance(from_mimetype, basestring):
        from_mimetypes.append(from_mimetype)
    else:
        from_mimetypes.extend(list(from_mimetype))

    to_mimetype = kwargs.pop('to_mimetype', 'text/html')
    assert to_mimetype, ('to_mimetype wird benoetigt! (%(to_mimetype)r)'
                         ) % locals()

    if 'default_output_type' in kwargs:
        default_output_type = kwargs.pop('default_output_type')
    elif to_mimetype == 'text/html':
        default_output_type = 'text/x-html-safe'
    else:
        default_output_type = None
    # --------------------------- ] ... Argumente für die Konversion ]

    assert not kwargs, 'Nicht erkannte Argumente: %s' % (kwargs,)

    def fix_types(instance=None, brain=None):
        # Docstring-Generierung: siehe unten
        instance, iinfo = instance_and_label(instance, brain, verbose)
        schema = instance.Schema()
        changed = False
        if verbose:
            tell(BASE, 'fixing types for %(iinfo)s ...', locals())
        for field in schema.values():
            name = field.__name__
            if skip(name):
                continue
            tell(DEBUG, 'field: name=%(name)r,'
                        ' field=%(field)r', locals())
            # nur schreibbare Felder:
            try:
                mutator = field.getMutator(instance)
                if mutator is None:
                    counter[('skipped', name, 'readonly')] += 1
                    tell(SKIP, 'field %(name)r is readonly', locals())
                    continue
            except AttributeError as e:
                counter[('skipped', name, 'AttributeError', 'getMutator')] += 1
                tell(BASE, 'AttributeError: getMutator')
                continue
            try:
                base_unit = field.getBaseUnit(instance)
            except AttributeError as e:
                counter[('skipped', name, 'AttributeError', 'getBaseUnit')] += 1
                tell(BASE, 'AttributeError: getBaseUnit')
                continue
            tell(DEBUG, 'OK: Feld %(name)r hat Mutator und BaseUnit', locals())
            mimetype = base_unit.mimetype
            if (from_mimetypes is not None
                and mimetype not in from_mimetypes
                ):
                tell(SKIP, 'skipping %(mimetype)r field %(name)r', locals())
                counter[('skipped', name, 'type', mimetype)] += 1
                continue
            args = []
            kwargs = {}
            if not base_unit:
                args.append(field.getDefault(instance))
                tell(CHANGE, 'creating field %(name)r', locals())
                kwargs['_initializing_'] = True
            if mimetype != to_mimetype or not base_unit:
                kwargs['mimetype'] = to_mimetype
            if (default_output_type
                    and field.default_output_type != default_output_type):
                kwargs['default_output_type'] = default_output_type
            if args or kwargs:
                kwargs.update({'field': name,
                               })
                if not args:
                    tell(DEBUG, 'Getting existing value for %(name)r ...', locals())
                    oldval = base_unit.getRaw()
                    args.append(oldval)
                    tell(CHANGE, 'using raw value %(oldval)r for field %(name)r', locals())
                tell(CHANGE, 'rectifying field %(name)r', locals())
                counter[('change', name)] += 1
                mapply(mutator, *args, **kwargs)
                changed = True
            else:
                tell(NOP, 'checked field %(name)r', locals())

        if changed:
            counter['changed'] += 1
            if verbose:
                tell(BASE, 'fixing types for %(iinfo)s: DONE', locals())
        else:
            counter['unchanged'] += 1
            if verbose:
                tell(BASE, 'fixing types for %(iinfo)s: NOTHING TO DO', locals())
        return instance

    fix_types.__doc__ = """
        Korrigiere MIME-Typen für das übergebene Objekt

        from_mimetypes =      %(from_mimetypes)s
        to_mimetype =         %(to_mimetype)r
        default_output_type = %(default_output_type)r
        """ % locals()
    return fix_types


def getter_name(a):
    """
    >>> getter_name('userId')
    'getUserId'
    """
    return 'get%s%s' % (a[0].upper(), a[1:])


def getter_tuple(a):
    """
    Gib ein 2-Tupel aus Feldname und Getter-Name zurück
    """
    return (a, getter_name(a))


def setter_name(a):
    """
    >>> setter_name('userId')
    'setUserId'
    """
    return 'set%s%s' % (a[0].upper(), a[1:])


def setter_tuple(a):
    """
    Gib ein 2-Tupel aus Feldname und Setter-Name zurück
    """
    return (a, setter_name(a))


def make_fields_inspector(**kwargs):
    """
    Erzeuge eine Funktion, die Informationen über bestimmte Felder ausgibt
    """
    # --------------------------- [ Argumente für die Ausführung ... [
    verbose = kwargs.pop('verbose', True)
    logger = kwargs.pop('logger', None)
    if verbose is None:
        verbose = logger is not None
    tell = make_minilogger(verbose, logger, 'inspect')

    if 'counter' in kwargs:
        counter = kwargs.pop('counter')
    else:
        counter = defaultdict(int)

    # zu inspizierende Attribute:
    fieldnames_good = makeSet(kwargs.pop('fieldnames_good', None))
    fieldnames_broken = makeSet(kwargs.pop('fieldnames_broken', None))
    skip = make_skip_function(tell,
                              sets=fieldnames_good+fieldnames_broken,
                              **kwargs)
    # --------------------------- ] ... Argumente für die Ausführung ]
    def this_cat(name):
        if name in fieldnames_good:
            return 2
        if name in fieldnames_broken:
            return 1
        return 0

    cat_label = ['Attribute ohne Einordnung:',
                 'Negativ-Beispiele:',
                 'Positiv-Beispiele:',
                 ]
    field_attributes = ['metatype',
                        'mimetype',
                        'default_output_type',
                        ]
    baseunit_attributes = ['mimetype',
                           ]

    def inspect_field(field, instance):
        """
        Funktion in Entwicklung ...
        """
        tell(BASE, '* Feld %r (%s):', field.__name__, field)
        has_attrs = set()
        lacks_attrs = set()
        field_value = {}
        for attr_name in field_attributes:
            try:
                attr = getattr(field, attr_name)
                has_attrs.add(attr_name)
                field_value[attr_name] = attr
                tell(BASE, '  %(attr_name)s: %(attr)r', locals())
            except AttributeError:
                lacks_attrs.add(attr_name)
        try:
            base_unit = field.getBaseUnit(instance)
            tell(BASE, '* %(base_unit)r:', locals())
        except AttributeError as e:
            tell(BASE, '  (keine BaseUnit)')
        else:
            for attr_name in baseunit_attributes:
                try:
                    attr = getattr(base_unit, attr_name)
                    if attr_name in has_attrs:
                        if attr == field_value[attr_name]:
                            suffix = ' (gleich)'
                        else:
                            suffix = ' (UNGLEICH)'
                    else:
                        suffix = ''
                    tell(BASE, '  - %(attr_name)s: %(attr)r%(suffix)s', locals())
                except AttributeError:
                    pass
            raw = base_unit.getRaw()
            tell(BASE, '  = %r', raw[:30])

    def inspect(instance=None, brain=None):
        instance, iinfo = instance_and_label(instance, brain, verbose)
        schema = instance.Schema()
        prev_cat = None
        for field in schema.values():
            name = field.__name__
            if skip(name):
                continue
            if prev_cat is None:
                tell(iinfo)
            curr_cat = this_cat(name)
            if curr_cat != prev_cat:
                tell(cat_label[curr_cat])
                prev_cat = curr_cat

            inspect_field(field, instance)
