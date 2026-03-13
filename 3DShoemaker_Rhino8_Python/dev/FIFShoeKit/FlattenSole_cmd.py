# -*- coding: utf-8 -*-
"""Flatten sole to 2D

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "FlattenSole"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] FlattenSole invoked.")
    Rhino.RhinoApp.WriteLine("  Flatten sole to 2D")
    return 0
