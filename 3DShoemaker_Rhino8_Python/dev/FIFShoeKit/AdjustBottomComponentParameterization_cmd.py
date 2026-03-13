# -*- coding: utf-8 -*-
"""Adjust bottom component parameters

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustBottomComponentParameterization"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustBottomComponentParameterization invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust bottom component parameters")
    return 0
