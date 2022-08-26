# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
visaplan.plone.tools._at1 -- imported via .attools

To replace the use of this one-liner (and use the imported functionality directly),
you can use the following vim script:

%s,^\(\s*\(#\s\?\)\)\(notify\)\(edit\)(\([^) ]\+\))\s*$,from zope import event\rfrom Products.Archetypes.event import ObjectEditedEvent\r\1event.\3(ObjectEditedEvent(\5)),e

This will give you two import lines before each converted code line; you'll need to move those up (and delete duplicates).
"""

# Python compatibility:
from __future__ import absolute_import

# Local imports:
from visaplan.plone.tools._have import HAS_ARCHETYPES

if HAS_ARCHETYPES:
    # Zope:
    from Products.Archetypes.event import ObjectEditedEvent
    from zope import event


def notifyedit(context):
    """
    trigger on-edited events for context
    """
    event.notify(ObjectEditedEvent(context))
