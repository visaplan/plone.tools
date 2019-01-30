.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

====================
visaplan.plone.tools
====================

General tools modules for Plone.

We don't claim ultimate Plone wisdom (yet); the main purpose of this package is
to factor out functionality from a big monolithic product into packages.

Thus, the purpose of this package (for now) is *not* to provide new functionality;
it is more likely to loose functionality during further development
(as parts of it will be forked out into their own packages,
or some functionality may even become obsolete because there are better
alternatives in standard Plone components).

It is part of the footing of the "Unitracc family" of Plone sites
which are maintained by visaplan GmbH, Bochum, Germany.

Some modules of this package still contain some resources (e.g. type names)
which are specific to our "Unitracc family" of sites;
this is likely to change in future releases.


Features
--------

This add-on can be seen in action at the following sites:

- https://www.unitracc.de
- https://www.unitracc.com

Modules in version 1.1.1:

- ``attools`` module

  several tools for Archetypes-based content

- ``brains`` module

  currently one ``make_collector`` function, e.g. for address fields

- ``cfg`` module

  Read "product" configuration, and detect development mode

- ``context`` module

  Several tools for processing the request.
  Some need some modernization ...

- ``forms`` module

  Several tools for forms

- ``functions`` module

  Some functions, e.g. ``is_uid_shaped``

- ``log`` module

  Automatically named loggers

- ``mock`` module

  - a few small classes for use in doctests

  - the same module as ``visaplan.tools.mock``

- ``mock_cfg`` module

  A rudimentary mock module for ``cfg``

- ``search`` module

  A few functions to support creation of ZODB catalog search queries
  (quite proprietary, I'm afraid; might go away in future versions)

- ``setup`` module (since v1.1)

  Functions for use in migration scripts

- ``zcmlgen`` module (since v1.1.1)

  - Generates ``configure.zcml`` files, if
    - changes are detected, and
    - development mode is active, and
    - the source is in an development package.


Documentation
-------------

Sorry, we don't have real user documentation yet.


Installation
------------

Since ``visaplan.plone.tools`` is a package for Plone instances,
it is not normally installed using ``pip``;
instead, install it by adding it to your buildout::

    [buildout]

    ...

    eggs =
        visaplan.plone.tools


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/visaplan/visaplan.plone.tools/issues
- Source Code: https://github.com/visaplan/visaplan.plone.tools


Support
-------

If you are having issues, please let us know;
please use the issue tracker mentioned above.


License
-------

The project is licensed under the GPLv2.

.. vim: tw=79 cc=+1 sw=4 sts=4 si et
