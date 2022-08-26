# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import, print_function

from six import iteritems as six_iteritems
from six import text_type as six_text_type

# Zope:
from Products.CMFCore.utils import getToolByName

# visaplan:
from visaplan.tools.lands0 import list_of_strings

# Local imports:
from visaplan.plone.tools.context import make_translator

try:
    # visaplan:
    from visaplan.tools.coding import safe_decode
except ImportError:
    if __name__ != '__main__':
        raise
    def safe_decode(s):
        if isinstance(s, six_text_type):
            return s
        return s.decode('utf-8')

