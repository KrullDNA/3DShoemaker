# -*- coding: utf-8 -*-
"""Update the current last geometry

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "UpdateLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] UpdateLast invoked.")
    Rhino.RhinoApp.WriteLine("  Update the current last geometry")
    return 0
