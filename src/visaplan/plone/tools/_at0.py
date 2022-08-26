# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
visaplan.plone.tools._at0 -- imported via .attools
"""

# Python compatibility:
from __future__ import absolute_import

# Local imports:
from visaplan.plone.tools._have import HAS_ARCHETYPES

if HAS_ARCHETYPES:
    # Zope:
    from Products.Archetypes.utils import mapply, shasattr


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
