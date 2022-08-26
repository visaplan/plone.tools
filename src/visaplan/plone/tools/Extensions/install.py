# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et nopaste cul tw=79 cc=+1
# taken from: http://blog.keul.it/2013/05/how-to-make-your-plone-add-on-products.html
#            (but using getToolByName)

# Python compatibility:
from __future__ import absolute_import

# Zope:
from Products.CMFCore.utils import getToolByName


def uninstall(portal):
    tool = getToolByName(portal, 'portal_setup')
    tool.runAllImportStepsFromProfile('profile-visaplan.plone.tools:uninstall')
