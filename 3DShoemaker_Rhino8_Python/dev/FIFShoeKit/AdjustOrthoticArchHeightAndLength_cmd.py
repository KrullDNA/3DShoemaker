# -*- coding: utf-8 -*-
"""Modify orthotic arch height and length

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustOrthoticArchHeightAndLength"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustOrthoticArchHeightAndLength invoked.")
    Rhino.RhinoApp.WriteLine("  Modify orthotic arch height and length")
    return 0
