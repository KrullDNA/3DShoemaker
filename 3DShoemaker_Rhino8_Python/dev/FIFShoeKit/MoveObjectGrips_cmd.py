# -*- coding: utf-8 -*-
"""Move object control points

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "MoveObjectGrips"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] MoveObjectGrips invoked.")
    Rhino.RhinoApp.WriteLine("  Move object control points")
    return 0
