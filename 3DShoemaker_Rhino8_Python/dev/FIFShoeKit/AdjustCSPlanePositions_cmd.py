# -*- coding: utf-8 -*-
"""Adjust cross-section plane positions

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustCSPlanePositions"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustCSPlanePositions invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust cross-section plane positions")
    return 0
