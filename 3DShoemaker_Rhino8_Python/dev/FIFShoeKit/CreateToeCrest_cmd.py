# -*- coding: utf-8 -*-
"""Create a toe crest

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateToeCrest"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateToeCrest invoked.")
    Rhino.RhinoApp.WriteLine("  Create a toe crest")
    return 0
