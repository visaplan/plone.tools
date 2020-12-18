Changelog
=========



2.0.0 (unreleased)
------------------

- Breaking changes:

  - ``forms.tryagain_url``:

    - all options (which are all arguments except the request)
      will `need to` be given by name
      (which is possible and `recommended already`).


1.3.0 (2020-12-16)
------------------

New Features:

- New module ``groups``

- New `.context` functions

  - `getMessenger` (factory):

    creates a `message` function which doesn't require
    (nor accept) a `context` argument

  - `getPath`
  - `get_parent`
  - `parents`
  - `parent_brains`
  - `make_brainGetter`
  - `make_pathByUIDGetter`
  - `make_translator`
  - `get_published_templateid`
  - `getSupportedLanguageTuples`

- New function ``setup.safe_context_id``

- New function ``search.normalizeQueryString`` (unicode, asterisks)

- `POSKeyError` rescue facility, *for now* provided here:

  Inspired by the  five.grok_-based ``@@fix-blobs`` view by Mikko Ohtamaa,
  we have two views:

  - ``@@check-blobs`` scans the site object tree for
    (Archetypes or Dexterity) objects with broken BLOB attachments
    (images or files) and shows them in an HTML list with checkboxes;

  - ``@@check-blobs-delete-selected`` allows to delete the objects
    found be be affected.

  *Note:* this functionality will likely be moved to a dedicated add-on package;
  don't rely on it to exist in *any* other release of this package!

- Optional functionality, depending on

  - visaplan.plone.search v1.2.1+
  - visaplan.plone.subportals

  (both currently not yet on PyPI)

Improvements:

- ``setup`` module:

  - If the ``reindex`` function, which was created by the ``make_reindexer`` factory,
    was given an object both by `brain` and by itself, it compared those two by identity,
    which wouldn't ever match.  Now checking for equality.

  - New function ``clone_tree`` (from release 1.2.0) now works recursively

  - When ``clone_tree`` moves objects from one folder to another, it tries to preserve a useful order;
    both functions ``_clone_tree_inner`` and ``_move_objects`` use the new helper ``apply_move_order_options``
    to inject a ``sort_on`` key into the query.

- ``context`` module:

  - ``message`` function (non-generated; with `context` argument):

    The default `mapping` is `None` now.

  - `make_permissionChecker` doesn't require the ``checkperm``
    adapter any more to be useful

  - `make_userdetector` doesn't require the ``auth``
    adapter any more to be useful

- Working doctests for ``search`` module

- ``zcmlgen`` module:

  - "Constructors" of the generator classes support an optional `skip` argument
    (keyword-only)

Hard dependencies removed:

- Products.Archetypes_

  if it is not installed, parts of the `.attools` module simply won't work

- visaplan.kitchen_

- visaplan.plone.infohubs_

  If not installed, `.forms.form_changes` *requires* a `form` argument
  (but it is a stub anyway).

[tobiasherp]


1.2.0 (2020-05-13)
------------------

New utilities:

- ``setup`` module:

  - New function ``clone_tree``, using
  - function factory ``make_object_getter``
    and
  - function factory ``make_subfolder_creator``

  Both factories have overlapping functionality and might become unified in a future version;
  their initial purposes were:

  ``make_object_getter`` creates a function (usually called ``get_object``)
  which tries to *find* a (possibly moved and/or renamed) object,
  and then is able to apply a few changes;

  ``make_subfolder_creator`` creates a function (usually called ``new_folder``)
  which creates a new *folder* (unless already present),
  and then is able to apply a few changes.

[tobiasherp]


1.1.6 (2019-11-27)
------------------

New modules:

- ``decorators`` module:

  - ``@returns_json``
    (uses simplejson_ if available)

New utilities:

- ``context`` module:

  - function factory ``make_timeformatter``

Bugfixes:

- Typo in README corrected.

[tobiasherp]


1.1.5 (2019-07-18)
------------------

Bugfixes:

- ``getConfiguration`` might fail; in such cases, log a warning and use the default
- Missing requirements:

  - visaplan.kitchen_

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

  - the same module as visaplan.tools_ .mock

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

.. _five.grok: https://pypi.org/project/five.grok
.. _Products.Archetypes: https://pypi.org/project/Products.Archetypes
.. _simplejson: https://pypi.org/project/simplejson
.. _visaplan.kitchen: https://pypi.org/project/visaplan.kitchen
.. _visaplan.plone.infohubs: https://pypi.org/project/visaplan.plone.infohubs
.. _visaplan.tools: https://pypi.org/project/visaplan.tools
