# -*- coding: utf-8 -*- äöü vim: sw=4 sts=4 et tw=79
# Python compatibility:
from __future__ import absolute_import

from six.moves import map

# Standard library:
from posixpath import normpath
from string import capitalize


def _traversable_path(path):
    """
    Little helper to remove a leading slash (and trailing slashes as well)
    which the .restrictedTraverse method seems to dislike.

    >>> _traversable_path('/e-learning/')
    'e-learning'

    Note: The method will still raise a KeyError if fht object is not yet there!
    """
    res = normpath(path)
    if res.startswith('/'):
        return res[1:]
    return res


def make_title(id):
    """
    A factory for default titles

    >>> make_title('with-dashes_and_underScores')
    'With Dashes And Underscores'
    """
    raw = id.strip()
    if not raw:
        raise ValueError('Nothing to build a title from: %(id)r' % locals())
    chunks = raw.replace('_', ' ').replace('-', ' ').split()
    res = ' '.join(map(capitalize, chunks))
    if not res:
        raise ValueError('Nothing left to build a title from: %(id)r' % locals())
    return res


if __name__ == '__main__':
    # Standard library:
    import doctest
    doctest.testmod()
