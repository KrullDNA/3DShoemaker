# -*- coding: utf-8 -*-
"""Adjust surfacing curve control points

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustSurfacingCurveControlPointPosition"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustSurfacingCurveControlPointPosition invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust surfacing curve control points")
    return 0
