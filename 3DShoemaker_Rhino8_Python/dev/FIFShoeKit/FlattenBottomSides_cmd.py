# -*- coding: utf-8 -*-
"""Flatten bottom sides to 2D

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "FlattenBottomSides"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] FlattenBottomSides invoked.")
    Rhino.RhinoApp.WriteLine("  Flatten bottom sides to 2D")
    return 0
