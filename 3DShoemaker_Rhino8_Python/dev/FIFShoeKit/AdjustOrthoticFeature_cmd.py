# -*- coding: utf-8 -*-
"""Adjust orthotic features

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustOrthoticFeature"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustOrthoticFeature invoked.")
    Rhino.RhinoApp.WriteLine("  Adjust orthotic features")
    return 0
