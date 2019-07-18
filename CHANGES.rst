Changelog
=========


1.2 (unreleased)
----------------

- Breaking changes:

  - ``forms.tryagain_url``:

    - all options (which are all arguments except the request) will need to be given by name
      (which is possible and recommended already).


1.1.5 (2019-07-18)
------------------

Bugfixes:

- `getConfiguration` might fail; in such cases, log a warning and use the default
- Missing requirements:

  - ``visaplan.kitchen``

[tobiasherp]


1.1.4 (2019-05-09)
------------------

- ``indexes`` module added:

  - Function ``getSortableTitle`` for title conversion.

    This converts umlauts etc. to sort them
    as equal to their corresponding base vocals,
    according to German lexical usage.

- ``attools`` module:

  - New function ``notifyedit(context)``

- ``forms`` module:

  - ``tryagain_url`` function supports ``var_items`` argument

  - bugfix for ``make_input`` function (suppression of ``type`` attribute)

- ``zcmlgen`` module:

  - changes detection improved to explicitly ignore added/removed blank lines

- ``context`` module:

  - new functions ``message`` and ``getbrain``,
    as replacement for some adapters named alike

[tobiasherp]


1.1.3 (2019-01-29)
------------------

- ``setup.make_renamer()``: generated ``rename`` function improved:
  existing positional options default to ``None``; instead of ``uid``,
  ``o`` (object) or ``brain`` can be specified (by name).

- ``setup.make_query_extractor()``, generated ``extract_query`` function improved:
  don't convert a ``Language`` string to a list if it's value is ``all``

- ``zcmlgen`` module:

  - Bugfix for changes detection

  - If changes are found but disallowed (non-development setup),
    and if ``sys.stdout`` is connected to a terminal,
    start the debugger

  [tobiasherp]


1.1.2 (2018-11-21)
------------------

- Corrections for the documentation

- (currently) unused dependencies removed
  [tobiasherp]


1.1.1 (2018-09-27)
------------------

- ``zcmlgen`` module added:

  - Generates ``configure.zcml`` files, if

    - changes are detected (*buggy*; see v1.1.3), and

    - development mode is active, and

    - the source is in a development package.


1.1 (2018-09-17)
----------------

- ``attools`` module added:

  - a brown bag of tools for Archetypes

- ``brains`` module added:

  - ``make_collector``, e.g. for address fields

- ``forms`` module added:

  - a brown bag of modules to support forms in a Zope/Plone system

- ``mock`` module added:

  - a few small classes for use in doctests

  - the same module as ``visaplan.tools.mock``

- ``mock_cfg`` module added:

  - accompanies ``cfg``, for testing only

- ``search`` module added:

  - tools for creation of catalog queries

- ``setup`` module added: functions for use in migration scripts

- Module changes:

  - ``context`` module:

    - new function ``decorated_tool``

  - ``functions`` module:

    - new function ``looksLikeAUID`` (for historical reasons)


1.0 (2018-07-11)
----------------

- Initial release.
  [tobiasherp]
