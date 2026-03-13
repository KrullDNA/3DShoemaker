# -*- coding: utf-8 -*-
"""Adjust orthotic to fit a blank

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustOrthoticToBlank"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustOrthoticToBlank invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust orthotic to fit a blank")
    return 0
