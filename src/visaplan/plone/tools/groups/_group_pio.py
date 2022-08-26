# -*- coding: utf-8 -*- äöü vim: ts=8 sts=4 sw=4 si et hls tw=79
# Python compatibility:
from __future__ import absolute_import

def _parse_init_options(kwdict, args):
    """
    Parse the options given during initialization

    We used to have 3 optional arguments which were normally specified
    positionally.  That's not ideal; optional arguments should better be given
    by name.  We don't enforce this yet, for compatibility reasons; but we like
    to have some testability.

    This function takes a dict of keyword arguments, and the tuple of
    positional arguments; it puts all information in that dict, which is
    changed in-place.

    >>> kw = {}
    >>> ar = ()
    >>> _parse_init_options(kw, ar)
    >>> sorted(kw.items())                     # doctest: +NORMALIZE_WHITESPACE
    [('forlist',    0),
     ('pretty',     0),
     ('searchtext', 0)]

    >>> kw.clear()
    >>> _parse_init_options(kw, (1, 2, 3))
    >>> sorted(kw.items())                     # doctest: +NORMALIZE_WHITESPACE
    [('forlist',    2),
     ('pretty',     1),
     ('searchtext', 3)]
    """
    unsupported = set(kwdict) - set([
        'forlist',
        'pretty',
        'searchtext'])
    if unsupported:
        unsupported = sorted(unsupported)
        raise TypeError('Unsupported keyword option(s) %(unsupported)s!'
                        % locals())
    if isinstance(args, tuple):
        args = list(args)
    # these used to be accepted positionally:
    if 'pretty' not in kwdict:
        kwdict['pretty'] = (args.pop(0) if args
                            else 0)
    if 'forlist' not in kwdict:
        kwdict['forlist'] = (args.pop(0) if args
                             else 0)
    if 'searchtext' not in kwdict:
        kwdict['searchtext'] = (args.pop(0) if args
                                else 0)
    if args:
        if args[1:]:
            raise TypeError('Unsupported positional options %r (...)'
                            % tuple(args[:1]))
        else:
            raise TypeError('Unsupported positional option %(args)s'
                            % locals())


if __name__ == '__main__':
    import doctest
    doctest.testmod()
