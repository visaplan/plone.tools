# -*- coding: utf-8 -*- vim: ts=8 sts=4 sw=4 si et tw=79
"""\
attools - Archetype tools

Products.Archetypes should be installed to use this module;
otherwise, some functions will fail
"""

# Python compatibility:
from __future__ import absolute_import, print_function

__author__ = "Tobias Herp <tobias.herp@visaplan.com>"

# Local imports:
from ._at0 import initialize_rich_text_fields
from ._at1 import notifyedit
from ._at2 import (
    make_fields_inspector,
    make_mimetype_fixer,
    make_minilogger,
    make_skip_function,
    )
from ._at3 import (
    getter_name,
    getter_tuple,
    instance_and_label,
    setter_name,
    setter_tuple,
    )
from ._at4 import get_first_text_as_html
from ._at5 import generate_all_texts, get_all_texts
