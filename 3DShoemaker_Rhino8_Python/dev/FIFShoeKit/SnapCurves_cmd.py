# -*- coding: utf-8 -*-
"""Snap curves to surfaces

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "SnapCurves"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] SnapCurves invoked.")
    Rhino.RhinoApp.WriteLine("  Snap curves to surfaces")
    return 0
