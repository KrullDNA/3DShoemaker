# -*- coding: utf-8 -*-
"""Blend between two surfaces

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "BlendSurfaceToSurface"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] BlendSurfaceToSurface invoked.")
    Rhino.RhinoApp.WriteLine("  Blend between two surfaces")
    return 0
