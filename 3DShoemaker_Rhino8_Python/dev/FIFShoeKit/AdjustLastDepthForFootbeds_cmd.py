# -*- coding: utf-8 -*-
"""Adjust last depth for footbeds

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustLastDepthForFootbeds"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustLastDepthForFootbeds invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust last depth for footbeds")
    return 0
