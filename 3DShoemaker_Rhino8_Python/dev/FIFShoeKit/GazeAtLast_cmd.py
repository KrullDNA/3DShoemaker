# -*- coding: utf-8 -*-
"""Set the viewport to look at the last

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "GazeAtLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] GazeAtLast invoked.")
    Rhino.RhinoApp.WriteLine("  Set the viewport to look at the last")
    return 0
