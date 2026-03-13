# -*- coding: utf-8 -*-
"""Adjust footbed depth

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustFootbedDepth"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustFootbedDepth invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust footbed depth")
    return 0
