# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""
visaplan.plone.tools.env: Information about the Zope environment
"""

# Python compatibility:
from __future__ import absolute_import

from os import environ
from os.path import basename


def worker_name(_env=None):
    """
    Return the name of the worker, e.g. 'client1'

    For long-running processes, e.g. upgrade steps, we might want to know the
    worker process which executes them; that way we are able to exclude that
    worker temporarily from the load balancing.

    We accept the `_env` option for testability only.

    >>> e = dict(INSTANCE_HOME='/opt/zope/parts/instance')
    >>> worker_name(e)
    'instance'
    """
    if _env is None:
        _env = environ
    home = _env.get('INSTANCE_HOME')
    if home:
        worker = basename(home)
        return worker or None


if __name__ == '__main__':
    import doctest
    doctest.testmod()
