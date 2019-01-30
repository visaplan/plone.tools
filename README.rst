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


Features
--------

This add-on can be seen in action at the following sites:

- https://www.unitracc.de
- https://www.unitracc.com

Modules in version 1.1:

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

- ``setup`` module (since v1.1)

  Functions for use in migration scripts


Documentation
-------------

The modules are documented by doctests.
Full documentation for end users can be found in the "docs" folder.


Translations
------------

This product has been translated into

- Klingon (thanks, K'Plai)


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
