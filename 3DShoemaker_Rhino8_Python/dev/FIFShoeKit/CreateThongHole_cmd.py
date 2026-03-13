# -*- coding: utf-8 -*-
"""Create a thong hole in the sole

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateThongHole"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateThongHole invoked.")
    Rhino.RhinoApp.WriteLine("  Create a thong hole in the sole")
    return 0
