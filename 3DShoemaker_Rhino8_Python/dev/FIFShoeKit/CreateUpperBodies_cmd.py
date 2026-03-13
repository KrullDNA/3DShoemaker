# -*- coding: utf-8 -*-
"""Generate upper pattern bodies

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateUpperBodies"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateUpperBodies invoked.")
    Rhino.RhinoApp.WriteLine("  Generate upper pattern bodies")
    return 0
