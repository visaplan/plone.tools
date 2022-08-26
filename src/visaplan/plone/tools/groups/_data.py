# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79

# Python compatibility:
from __future__ import absolute_import


class PrettyMask(dict):
    """
    For every given "role", suggest a mask for a "pretty" group title.

    >>> PM = PrettyMask(u'%s group "{group}"')
    >>> PM['Reader']
    u'Reader group "{group}"'
    """
    def __init__(self, mask, func=None):
        self._mask = mask
        self._checkfunc = func

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            val = self._mask % (key,)
            dict.__setitem__(self, key, val)
            return dict.__getitem__(self, key)


PRETTY_MASK = PrettyMask(u'%s group "{group}"')


if __name__ == '__main__':
    # Standard library:
    from doctest import testmod
    testmod()
