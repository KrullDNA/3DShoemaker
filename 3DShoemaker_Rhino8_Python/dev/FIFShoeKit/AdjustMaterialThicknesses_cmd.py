# -*- coding: utf-8 -*-
"""Set material layer thicknesses

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustMaterialThicknesses"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustMaterialThicknesses invoked.")
    Rhino.RhinoApp.WriteLine("  Set material layer thicknesses")
    return 0
