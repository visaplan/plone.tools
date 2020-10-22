.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide.html
   This text does not appear on pypi or github. It is a comment.

.. image::
   https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
       :target: https://pycqa.github.io/isort/

====================
visaplan.plone.tools
====================

General tools modules for Plone_.

We don't claim ultimate Plone wisdom (yet);
this package is one of the parts a big monolithic classic Zope product
was split into.

It is part of the footing of the "Unitracc family" of Plone sites
which are maintained by `visaplan GmbH`_, Bochum, Germany.

Some modules of this package might still contain some resources
(e.g. type names)
which are specific to our "Unitracc family" of sites;
this is likely to change in future releases.


Features
--------

This add-on can be seen in action at the following sites:

- https://www.unitracc.de
- https://www.unitracc.com

Modules in version 1.1.4+:

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

- ``indexes`` module (new in v1.1.4) 

  - Function ``getSortableTitle`` for title conversion.

    This converts umlauts etc. to sort them
    as equal to their corresponding base vocals,
    according to German lexical usage.

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

- ``decorators`` module (since v1.1.6)

  - ``@returns_json``:

    Wraps the function call and returns the JSON_-encoded result,
    including HTTP headers.

    Uses simplejson_ if available.

Documentation
-------------

Sorry, we don't have real user documentation yet.

Most functions are documented by doctests, anyway;
it helps to understand some German.


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

- Issue Tracker: https://github.com/visaplan/plone.tools/issues
- Source Code: https://github.com/visaplan/plone.tools


Support
-------

If you are having issues, please let us know;
please use the `issue tracker`_ mentioned above.


License
-------

The project is licensed under the GPLv2.

.. _`issue tracker`: https://github.com/visaplan/plone.tools/issues
.. _JSON: https://json.org/
.. _Plone: https://plone.org/
.. _simplejson: https://pypi.org/project/simplejson
.. _`visaplan GmbH`: http://visaplan.com

.. vim: tw=79 cc=+1 sw=4 sts=4 si et
