# -*- coding: utf-8 -*-
"""Set material properties

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustMaterial"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustMaterial invoked.")
    Rhino.RhinoApp.WriteLine("  Set material properties")
    return 0
